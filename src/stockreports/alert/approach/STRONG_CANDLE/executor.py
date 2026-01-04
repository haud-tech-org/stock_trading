# src/stockreports/alert/approach/STRONG_CANDLE/executor.py
import pandas as pd
import logging
import json

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    _is_rsi_not_exhausted,
    is_signal_confirmed
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.common.regime import has_divergence
from .settings import StrongCandleSettings


class StrongCandleExecutor(Executor):
    APPROACH_NAME = Approach.STRONG_CANDLE

    def __init__(self, symbol: str):
        self.settings = StrongCandleSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the Strong Candle approach. It identifies candles with
        a strong close and a small tail, indicating decisive momentum.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_strong_candle_alerts(df, new_candle_count)
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

    def _find_strong_candle_alerts(self, df: pd.DataFrame, new_candle_count=0) -> list[AlertData]:
        """
        Finds alerts based on a state machine pattern, using a unified reverse loop.
        This function is optimized for both DEPLOYMENT (latest alert) and DEVELOPMENT (all alerts) modes.
        """
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        confirmation_window = self.settings.confirmation_window
        required_lookback = confirmation_window + 2

        df = prepare_indicators(df)
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts
        
        df_indexed = df.reset_index()

        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            momentum_candle = df_indexed.iloc[i]
            confirmation_candle = df_indexed.iloc[i-1]

            is_bullish_momentum = momentum_candle['close'] > confirmation_candle['close']
            is_bearish_momentum = momentum_candle['close'] < confirmation_candle['close']
            
            if not (is_bullish_momentum or is_bearish_momentum):
                continue
            
            potential_signal = Signal.BUY if is_bullish_momentum else Signal.SELL

            if not is_signal_confirmed(confirmation_candle, potential_signal, self.settings.approach_settings):
                continue

            # --- 4. Volume Confirmation (Optional) ---
            if self.settings.use_volume_confirmation:
                if not can_apply_volume_confirmation(df_indexed):
                    continue
                if not is_volume_spike_confirmed(df_indexed, i):
                    continue
            
            if self.settings.use_last_candle_max_volume_confirmation:
                if not can_apply_volume_confirmation(df_indexed):
                    continue
                # Create a window ending at i to check if the last candle (at i) has max volume
                # The window size isn't strictly defined here, but typically we check against recent history.
                # Let's use the confirmation window + 2 (same as required_lookback logic)
                window_start = max(0, i - self.settings.confirmation_window - 1)
                volume_window = df_indexed.iloc[window_start : i + 1]
                if not is_last_candle_volume_max(volume_window):
                    continue

            if self.settings.use_volume_increasing_confirmation:
                if not can_apply_volume_confirmation(df_indexed):
                    continue
                # Similarly, define a window for increasing volume check
                window_start = max(0, i - self.settings.confirmation_window - 1)
                volume_window = df_indexed.iloc[window_start : i + 1]
                if not is_volume_increasing(volume_window):
                    continue

            if self.settings.use_divergence_confirmation:
                if not has_divergence(df_indexed, i, potential_signal):
                    continue

            strong_candle_found = False
            strong_candle = None
            
            search_window_start = max(0, i - 1 - confirmation_window)
            for j in range(i - 2, search_window_start - 1, -1):
                candidate_strong_candle = df_indexed.iloc[j]
                
                if pd.isna(candidate_strong_candle['body_size']):
                    continue

                is_strong_bullish = (
                    potential_signal == Signal.BUY and
                    candidate_strong_candle['close'] > candidate_strong_candle['open'] and
                    candidate_strong_candle['body_size'] > self.settings.min_expected_profit_loss and
                    candidate_strong_candle['upper_wick'] < candidate_strong_candle['body_size'] * self.settings.trend_strength_strong_close_tail_ratio
                )
                is_strong_bearish = (
                    potential_signal == Signal.SELL and
                    candidate_strong_candle['close'] < candidate_strong_candle['open'] and
                    candidate_strong_candle['body_size'] > self.settings.min_expected_profit_loss and
                    candidate_strong_candle['lower_wick'] < candidate_strong_candle['body_size'] * self.settings.trend_strength_strong_close_tail_ratio
                )

                if is_strong_bullish or is_strong_bearish:
                    strong_candle = candidate_strong_candle
                    strong_candle_found = True
                    break

            if not strong_candle_found:
                continue

            # --- New conditions for comparing momentum candle to strong candle ---
            if potential_signal == Signal.BUY:
                # 1. The open of the momentum candle must be higher than the strong candle's open.
                if momentum_candle['open'] <= strong_candle['open']:
                    continue
            
            elif potential_signal == Signal.SELL:
                # 1. The open of the momentum candle must be lower than the strong candle's open.
                if momentum_candle['open'] >= strong_candle['open']:
                    continue
            else:
                continue # Should not happen

            # 2. The close of the momentum candle must be higher/lower than the strong candle's close (checked by magnitude).
            start_price = strong_candle['close']
            is_sufficient, magnitude = check_magnitude(momentum_candle['close'], start_price, self.settings.min_alert_magnitude)
            if not is_sufficient:
                continue

            strong_candle_index = strong_candle.name
            if strong_candle_index > 0:
                candle_before_strong = df_indexed.iloc[strong_candle_index - 1]
                candles_for_exhaustion_check = [candle_before_strong]
                
                if not _is_rsi_not_exhausted(candles_for_exhaustion_check, potential_signal, self.settings.approach_settings):
                    continue

            volume_window_df = df_indexed.iloc[strong_candle.name : i + 1]
            use_volume_spike = self.settings.use_volume_confirmation
            use_increasing_volume = self.settings.use_volume_increasing_confirmation
            use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

            volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
            volume_is_increasing = not use_increasing_volume or is_volume_increasing(volume_window_df)
            last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(volume_window_df)

            if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
                continue

            alert_time = momentum_candle['time']
            start_time = strong_candle['time']
            if isinstance(start_time, pd.Timestamp):
                start_time = start_time.isoformat()
            alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

            details = {
                "strong_candle_time": strong_candle['time'].isoformat(),
                "confirmation_candle_time": confirmation_candle['time'].isoformat(),
                "momentum_candle_time": alert_time.isoformat(),
                "strong_candle_body": round(strong_candle['body_size'], 2)
            }

            alert_data = AlertData(
                approach=self.APPROACH_NAME,
                id=alert_id,
                symbol=self.symbol,
                signal=potential_signal,
                alert_price=momentum_candle['close'],
                alert_time=alert_time,
                start_price=start_price,
                start_time=start_time,
                magnitude=magnitude,
                details=json.dumps(details)
            )
            alerts.append(alert_data)

            if not is_development_mode:
                return alerts
                
        return alerts[::-1]
