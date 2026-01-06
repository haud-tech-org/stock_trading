import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal, PeakTrough, PriceColumn
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    is_signal_confirmed,
    _is_rsi_not_exhausted
)
from src.stockreports.alert.common.data_utils import can_apply_analysis, find_extreme_point, find_nearest_extreme_point
from src.stockreports.alert.common.volume import (
    is_volume_spike_confirmed, 
    can_apply_volume_confirmation, 
    is_last_candle_volume_max,
    is_volume_increasing
)
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.utils.time_utils import to_iso8601_with_tz
from src.stockreports.alert.confirmation.reversal_trend.executor import ReversalConfirmationExecutor
from .settings import ConsistentMomentumSettings


class ConsistentMomentumExecutor(ReversalConfirmationExecutor):
    APPROACH_NAME = Approach.CONSISTENT_MOMENTUM
    LATEST_ACCEPTED_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):        
        super().__init__(symbol)
        self.settings = ConsistentMomentumSettings(symbol)
        self.logger = logging.getLogger(__name__)


    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the CONSISTENT_MOMENTUM approach. It takes a DataFrame and returns an AlertResult.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            df = prepare_indicators(df)

            alerts_data = self._find_consistent_momentum_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=pd.DataFrame(),
                status="FAILED",
                message=str(e)
            )

    def _analyze_window(self, window: pd.DataFrame, df_indexed: pd.DataFrame, confirmation_window: int) -> Optional[AlertData]:
        """
        Analyzes a single window of data to find a consistent momentum alert.
        """
        is_all_bullish = (window['close'] > window['open']).all()
        is_all_bearish = (window['close'] < window['open']).all()

        if not (is_all_bullish or is_all_bearish):
            return None

        window['avg_price'] = (window['open'] + window['close']) / 2
        
        is_momentum_confirmed = False
        if is_all_bullish:
            is_momentum_confirmed = window['avg_price'].is_monotonic_increasing
            signal = Signal.BUY
        elif is_all_bearish:
            is_momentum_confirmed = window['avg_price'].is_monotonic_decreasing
            signal = Signal.SELL
        
        if not is_momentum_confirmed:
            return None

        current_candle = window.iloc[-1]
        candle_range = (current_candle['high'] - current_candle['low'])
        if candle_range == 0: 
            return None

        # Restore momentum strength check (total body vs total wick)
        window['body'] = abs(window['close'] - window['open'])
        window['range'] = window['high'] - window['low']
        window['wick'] = window['range'] - window['body']

        total_body = window['body'].sum()
        total_wick = window['wick'].sum()

        if total_body <= total_wick:
            return None

        # Restore RSI exhaustion check
        start_candle = window.iloc[0]
        end_candle = window.iloc[-1]
        candles_for_rsi_check = [start_candle, end_candle]

        if not _is_rsi_not_exhausted(candles_for_rsi_check, signal, self.settings):
            return None

        # Restore general signal confirmation (MA, ADX, etc.)
        if not is_signal_confirmed(end_candle, signal, self.settings):
            return None

        # The breakout confirmation logic has been moved to the main loop
        # to allow for forward-window analysis.

        use_volume_spike = self.settings.use_volume_confirmation
        use_increasing_volume = self.settings.use_volume_increasing_confirmation
        use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

        confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
        confirmation_df = df_indexed.iloc[confirmation_candle_index - confirmation_window + 1 : confirmation_candle_index + 1]

        volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), confirmation_candle_index))
        volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)

        if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
            return None

        # --- Alert Confirmation and Generation ---
        # If forward window confirmation is not used, we stop here.
        if not self.settings.use_forward_window_confirmation:
            return None

        # If we proceed, it means forward window confirmation is required.
        confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
        
        # New Middle Confirmation Step
        if not self._confirm_significant_price_change(df_indexed, confirmation_candle_index, signal):
            return None
            
        confirmation_result = self._get_forward_window_confirmation(df_indexed, confirmation_candle_index, signal)
        
        # If the forward window does not confirm a breakout or reversal, no alert is generated.
        if confirmation_result is None:
            return None

        # Unpack the results
        final_candle, confirmed_signal = confirmation_result
        
        # Now that the final_candle is determined, generate the details.
        details = {
            "momentum_start_price": start_candle['open'],
            "momentum_start_time": to_iso8601_with_tz(start_candle.name),
            "momentum_window_size": confirmation_window,
            "reason": "Consistent Momentum with Breakout"
        }
        
        original_signal = signal
        if confirmed_signal != original_signal:
            details["reason"] = "Consistent Momentum with Reversal"
        
        details["breakout_lookback_minutes"] = self.settings.peak_bottom_lookback_period

        # Create the AlertData object with the final, confirmed data.
        alert_id = str(int(final_candle.name.tz_convert('UTC').timestamp()))
        current_price = final_candle['close']
        momentum_start_price = start_candle['open']

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            alert_time=final_candle.name,
            signal=confirmed_signal,
            alert_price=current_price,
            start_price=momentum_start_price,
            start_time=start_candle.name,
            magnitude=round(abs(current_price - momentum_start_price), 2),
            details=json.dumps(details)
        )

    def _get_forward_window_confirmation(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> Optional[tuple[pd.Series, Signal]]:
        """
        Confirms a breakout or reversal by analyzing the backward and forward windows.
        It first attempts to find a specific volume-climax reversal. If that fails,
        it falls back to a more general reversal confirmation.
        Returns a tuple of (confirmation_candle, confirmed_signal) if confirmed, otherwise None.
        """
        alert_candle_time = df_indexed.index[alert_candle_index]

        # 1. Analyze the backward window to confirm a breakout has occurred first.
        is_breakout_confirmed = self._confirm_breakout_price(
            df_indexed, 
            alert_candle_index, 
            signal,
            lookback_period=self.settings.peak_bottom_lookback_period,
            prominence=self.settings.peak_trough_prominence
        )
        if not is_breakout_confirmed:
            return None

        # 2. Primary Confirmation: Attempt to find a volume-climax reversal pattern first.
        forward_window_size = self.settings.long_forward_window
        forward_window_end = min(alert_candle_index + forward_window_size, len(df_indexed))
        
        # Attempt primary confirmation with the available forward data.
        forward_window = df_indexed.iloc[alert_candle_index:forward_window_end]
        reversal_candle = self._find_reversal_candle(forward_window, signal)

        if reversal_candle is not None:
            # Primary confirmation successful
            final_signal = Signal.SELL if signal == Signal.BUY else Signal.BUY
            self.logger.debug(f"[{alert_candle_time}] Confirmed reversal with _find_reversal_candle.")
            return reversal_candle, final_signal
        
        # 3. Fallback Confirmation: If primary fails, use the general reversal confirmation.
        self.logger.debug(f"[{alert_candle_time}] Primary confirmation failed, falling back to _confirm_reversal_in_forward_window.")
        confirmation_result = self._confirm_reversal_in_forward_window(df_indexed, alert_candle_index, signal)
        
        if confirmation_result is None:
            self.logger.debug(f"[{alert_candle_time}] No confirmation pattern was found in the forward window.")
            return None

        return confirmation_result

    def _confirm_significant_price_change(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> bool:
        """
        Confirms that the alert candle represents a significant price change from the nearest
        peak (for SELL) or trough (for BUY) in the lookback period.
        """
        alert_candle_time = df_indexed.index[alert_candle_index]
        alert_candle = df_indexed.iloc[alert_candle_index]

        # 1. Define the lookback period
        lookback_period = self.settings.peak_bottom_lookback_period
        lookback_start_index = max(0, alert_candle_index - lookback_period)
        lookback_df = df_indexed.iloc[lookback_start_index:alert_candle_index]

        if lookback_df.empty:
            self.logger.debug(f"[{alert_candle_time}] No lookback history available for significant price change check.")
            return True # Bypass if no history

        # 2. Find the nearest peak (for SELL) or trough (for BUY)
        # Note: We look for the opposite of the breakout logic. For a SELL signal, we look for a recent PEAK.
        extreme_type = PeakTrough.PEAK if signal == Signal.SELL else PeakTrough.TROUGH
        price_column = PriceColumn.CLOSE
        
        extreme_point_info = find_nearest_extreme_point(
            lookback_df, 
            price_column, 
            extreme_type, 
            self.settings.peak_trough_prominence
        )

        if extreme_point_info is None:
            self.logger.debug(f"[{alert_candle_time}] No opposing peak/trough found; skipping significant change check.")
            return True

        nearest_extreme_price, _ = extreme_point_info
        
        # 3. Check for significant difference
        price_diff = abs(alert_candle['close'] - nearest_extreme_price)
        
        if price_diff < self.settings.significant_price_change_threshold:
            self.logger.debug(f"[{alert_candle_time}] Price change of {price_diff:.2f} from nearest extreme ({nearest_extreme_price:.2f}) is not significant. Threshold: {self.settings.significant_price_change_threshold}")
            return False

        self.logger.debug(f"[{alert_candle_time}] Significant price change of {price_diff:.2f} confirmed.")
        return True

    def _find_consistent_momentum_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Finds alerts based on a consistent momentum pattern using a unified reverse loop.
        """
        alerts = []
        confirmation_window = self.settings.confirmation_window
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        if confirmation_window < 2:
            self.logger.error(f"{self.APPROACH_NAME}: 'CONFIRMATION_WINDOW' must be at least 2. Aborting.")
            return alerts

        required_lookback = confirmation_window
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        df_indexed = df.set_index('time')

        # The main loop can now run up to the last candle. The forward window logic
        # inside the confirmation function will handle boundaries.
        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In DEPLOYMENT, we must scan back far enough to catch momentum windows
            # that could be confirmed by one of the new candles.
            forward_window = self.settings.long_forward_window if self.settings.use_forward_window_confirmation else 0
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - forward_window)

        for i in range(loop_end, loop_start - 1, -1):
            # Ensure we don't look past the end of the dataframe for the momentum window.
            if i < confirmation_window - 1:
                continue

            window = df_indexed.iloc[i - confirmation_window + 1 : i + 1].copy()

            alert = self._analyze_window(window, df_indexed, confirmation_window)

            if alert:
                # Cooldown Check: Ignore alerts with the same direction within the cooldown period
                if ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT is not None:
                    time_since_last = alert.alert_time - ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT.alert_time
                    minutes_since_last = time_since_last.total_seconds() / 60

                    if (minutes_since_last < self.settings.cooldown_period and 
                        alert.signal == ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT.signal):
                        alert = None

                if alert:
                    alerts.append(alert)

                    # Update global state with the accepted alert
                    ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT = alert

                    if not is_development_mode:
                        return alerts

        return alerts[::-1]
