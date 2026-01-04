import pandas as pd
import logging
import json
from typing import Optional, List, Tuple

from scipy.signal import find_peaks

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.utils.time_utils import to_iso8601_with_tz
from .settings import VolumeSpikeConfirmationSettings

class VolumeSpikeConfirmationExecutor(Executor):
    APPROACH_NAME = Approach.VOLUME_SPIKE_CONFIRMATION
    LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None

    def __init__(self, symbol: str):
        self.settings = VolumeSpikeConfirmationSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the VOLUME_SPIKE_CONFIRMATION approach.
        Identifies reversal signals based on a two-phase "Climax and Reversal" logic.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame(), status="FAILED", message=str(e))

    def _find_reversal_candle(self, reversal_window: pd.DataFrame, expected_signal: Signal) -> Optional[pd.Series]:
        """
        Validates if the last candle in the window is a reversal candle.
        """
        if reversal_window.empty or len(reversal_window) < 2:
            return None

        candle = reversal_window.iloc[-1]
        prev_candle = reversal_window.iloc[-2]
        
        body_size = abs(candle['close'] - candle['open'])
        if body_size < self.settings.min_reversal_body_size:
            return None

        if expected_signal == Signal.BUY:
            is_bullish = candle['close'] > candle['open']
            is_price_reversing = candle['close'] > prev_candle['close']
            if is_bullish and is_price_reversing:
                return candle
        
        elif expected_signal == Signal.SELL:
            is_bearish = candle['close'] < candle['open']
            is_price_reversing = candle['close'] < prev_candle['close']
            if is_bearish and is_price_reversing:
                return candle
        
        return None

    def _validate_climax_event(self, lookback_window: pd.DataFrame) -> Optional[Tuple[pd.Series, Signal]]:
        """
        Identifies and validates a climax event within a lookback window.
        Returns the climax candle and the expected reversal signal if valid.
        """
        # Find the candle with the maximum volume in the window
        max_vol_candle = lookback_window.loc[lookback_window['volume'].idxmax()]
        max_vol_idx = lookback_window.index.get_loc(max_vol_candle.name)

        # Ensure the max volume candle is not too early or late in the window
        if max_vol_idx < 2 or max_vol_idx >= len(lookback_window) - 1:
            return None

        # --- Volume Validation ---
        prev_candle_1 = lookback_window.iloc[max_vol_idx - 1]
        prev_candle_2 = lookback_window.iloc[max_vol_idx - 2]
        
        vol_mult = self.settings.previous_candles_volume_multiplier
        if not (max_vol_candle['volume'] >= prev_candle_1['volume'] * vol_mult or
                max_vol_candle['volume'] >= prev_candle_2['volume'] * vol_mult):
            return None

        avg_volume_window = lookback_window['volume'].mean()
        if max_vol_candle['volume'] < self.settings.avg_volume_multiplier * avg_volume_window:
            return None

        # --- Trend Confirmation (leading up to the climax candle) ---
        trend_window = lookback_window.iloc[:max_vol_idx + 1]
        
        # Check for BUY Signal (Downtrend before climax)
        if not self.settings.disable_buy_signal:
            peak_args = {'prominence': self.settings.peak_trough_prominence} if self.settings.peak_trough_prominence is not None else {}
            peaks, _ = find_peaks(trend_window['close'], **peak_args)
            
            first_candle = trend_window.iloc[0]
            peak_prices = trend_window.iloc[peaks]['close'].tolist()
            trend_prices_sequence = [first_candle['close']] + peak_prices + [max_vol_candle['close']]
            
            is_downtrend = all(trend_prices_sequence[i] >= trend_prices_sequence[i+1] for i in range(len(trend_prices_sequence)-1))
            if is_downtrend:
                return max_vol_candle, Signal.BUY

        # Check for SELL Signal (Uptrend before climax)
        if not self.settings.disable_sell_signal:
            trough_args = {'prominence': self.settings.peak_trough_prominence} if self.settings.peak_trough_prominence is not None else {}
            troughs, _ = find_peaks(-trend_window['close'], **trough_args)

            first_candle = trend_window.iloc[0]
            trough_prices = trend_window.iloc[troughs]['close'].tolist()
            trend_prices_sequence = [first_candle['close']] + trough_prices + [max_vol_candle['close']]

            is_uptrend = all(trend_prices_sequence[i] <= trend_prices_sequence[i+1] for i in range(len(trend_prices_sequence)-1))
            if is_uptrend:
                return max_vol_candle, Signal.SELL
        
        return None

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int) -> List[AlertData]:
        """
        Main loop to find alerts based on the 'Climax and Search-to-End Reversal' pattern.
        """
        alerts = []
        lookback_window_size = self.settings.lookback_window
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=lookback_window_size):
            return alerts

        df_indexed = df.set_index('time')

        # --- Cooldown Check at the beginning ---
        if self.is_in_cooldown(
            latest_alert_timestamp=VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP,
            current_time=df_indexed.index[-1],
            cooldown_period=self.settings.cooldown_period
        ):
            # The check is true, so we are in cooldown. Log it.
            last_alert_time = VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP.tz_convert(None)
            current_time_naive = df_indexed.index[-1].tz_convert(None)
            time_since_last_alert = (current_time_naive - last_alert_time).total_seconds() / 60
            self.logger.info(
                f"'{self.APPROACH_NAME}' for {self.symbol} is in cooldown. "
                f"Last alert was {time_since_last_alert:.2f} minutes ago. "
                f"Cooldown is {self.settings.cooldown_period} minutes."
            )
            return alerts

        loop_end = len(df_indexed) - 1
        min_scan_index = lookback_window_size - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In deployment, only scan recent windows
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - 1)

        for i in range(loop_end, loop_start - 1, -1):
            window_start_index = i - lookback_window_size + 1
            if window_start_index < 0: continue
            
            lookback_window = df_indexed.iloc[window_start_index : i + 1]
            
            climax_result = self._validate_climax_event(lookback_window)
            if not climax_result:
                continue

            max_vol_candle, expected_signal = climax_result
            
            # Define the search space for the reversal candle (all candles after the climax)
            max_vol_candle_full_df_idx = df_indexed.index.get_loc(max_vol_candle.name)
            reversal_search_space = df_indexed.iloc[max_vol_candle_full_df_idx:]

            # The forward search space must be within the max size and contain at least 2 candles
            # (the climax candle and at least one subsequent candle for reversal).
            if len(reversal_search_space) > self.settings.max_forward_window_size or len(reversal_search_space) < 2:
                continue

            reversal_candle = self._find_reversal_candle(reversal_search_space, expected_signal)

            if reversal_candle is not None:
                start_candle_of_window = df_indexed.iloc[window_start_index]
                latest_candle_time = df_indexed.index[-1]
                
                details_dict = {
                    "reason": f"Volume Climax Reversal ({expected_signal})",
                    "climax_time": to_iso8601_with_tz(max_vol_candle.name),
                    "processed_time": to_iso8601_with_tz(latest_candle_time)
                }

                alert = AlertData(
                    approach=self.APPROACH_NAME,
                    id=str(int(reversal_candle.name.tz_convert('UTC').timestamp())),
                    symbol=self.symbol,
                    alert_time=reversal_candle.name,
                    signal=expected_signal,
                    alert_price=reversal_candle['close'],
                    start_price=start_candle_of_window['close'],
                    start_time=start_candle_of_window.name,
                    magnitude=round(abs(reversal_candle['close'] - start_candle_of_window['close']), 2),
                    details=json.dumps(details_dict)
                )

                # To prevent re-triggering on the same event in development mode
                # we can check if the new alert's climax time is the same as the last one.
                if is_development_mode and VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP:
                    # This check is now more complex as we don't store the full alert.
                    # For dev mode, we might need a more robust way to avoid duplicates if this becomes an issue.
                    # For now, we'll rely on the cooldown.
                    pass

                alerts.append(alert)
                VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP = latest_candle_time

                if not is_development_mode:
                    return alerts

        return alerts[::-1]
