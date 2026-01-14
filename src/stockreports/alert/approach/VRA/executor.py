import pandas as pd
from scipy.signal import find_peaks
import logging
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import VraSettings
from src.stockreports.alert.common.confirmation.reversal import validate_reversal_confirmation
from src.stockreports.utils.alert_utils import is_in_cooldown

class VraExecutor(Executor):
    APPROACH_NAME = Approach.VRA
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = VraSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_vra_alerts(df, new_candle_count)
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

    def _find_vra_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        window_size = self.settings.lookback_window

        if len(df) < window_size:
            self.logger.warning(f"Not enough data for {self.APPROACH_NAME}: requires {window_size}, have {len(df)}.")
            return alerts

        df_indexed = df.reset_index()

        # Standardized reverse loop setup from other executors
        loop_end_index = len(df_indexed) - 1
        min_scan_index = window_size - 1

        if is_development_mode:
            # In development, we analyze all possible windows
            loop_start_index = min_scan_index
        else:
            # In production, we only analyze the latest candles
            loop_start_index = max(min_scan_index, len(df_indexed) - new_candle_count)

        # Reverse loop from the most recent data to the oldest
        for i in range(loop_end_index, loop_start_index - 1, -1):
            window_start_index = i - window_size + 1
            window_df = df_indexed.iloc[window_start_index : i + 1].copy()

            # --- Validation Order for Performance ---

            # 1. Volume Spike Analysis (Cheap & High-Impact)
            volume_anchor_idx = window_df['volume'].idxmax()
            min_vol_idx = window_df['volume'].idxmin()

            if min_vol_idx >= volume_anchor_idx:
                continue
            
            candle_v = window_df.loc[volume_anchor_idx]
            min_vol_in_window = window_df.loc[min_vol_idx]['volume']
            if not (candle_v['volume'] >= self.settings.volume_multiplier * min_vol_in_window):
                continue

            # Define confirmation window and reversal signal
            confirmation_df = window_df.loc[volume_anchor_idx:].copy()
            if len(confirmation_df) < 2:
                continue
            
            first_candle = window_df.iloc[0]
            reversal_signal = Signal.SELL if candle_v['close'] > first_candle['close'] else Signal.BUY

            # Validate confirmation and get alert/anchor candles
            validation_result = validate_reversal_confirmation(
                confirmation_df, reversal_signal, self.settings.min_alert_body_size, self.settings.max_distance_close_price
            )
            if validation_result is None:
                continue
            
            alert_candle, anchor_candle = validation_result

            # 7. Magnitude Validation (Most Complex)
            if reversal_signal == Signal.SELL:
                min_close_in_window = window_df['close'].min()
                magnitude = abs(anchor_candle['close'] - min_close_in_window)
            else: # BUY
                max_close_in_window = window_df['close'].max()
                magnitude = abs(max_close_in_window - anchor_candle['close'])

            if magnitude < self.settings.min_trend_magnitude:
                continue
            
            # --- Cooldown Logic ---
            if is_in_cooldown(
                new_alert_time=alert_candle['time'],
                new_signal=reversal_signal,
                latest_alert=VraExecutor.LATEST_ALERT,
                cooldown_window=self.settings.cooldown_window
            ):
                self.logger.info(f"Skipping alert for {self.symbol} due to cooldown.")
                continue

            # --- All validations passed, create alert ---
            alert_time = alert_candle['time']
            alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

            alert_data = AlertData(
                approach=self.APPROACH_NAME,
                id=alert_id,
                symbol=self.symbol,
                signal=reversal_signal,
                alert_price=alert_candle['close'],
                alert_time=alert_time,
                start_price=window_df.iloc[0]['close'],
                start_time=window_df.iloc[0]['time'].isoformat(),
                magnitude=magnitude,
                details=json.dumps({
                    "volume_multiplier": self.settings.volume_multiplier,
                    "lookback_window": self.settings.lookback_window,
                    "anchor_candle_time": anchor_candle['time'].isoformat(),
                    "anchor_candle_price": anchor_candle['close']
                })
            )
            alerts.append(alert_data)
            VraExecutor.LATEST_ALERT = alert_data

            # In production mode, return immediately after finding the first valid alert
            if not is_development_mode:
                return alerts

        return alerts
