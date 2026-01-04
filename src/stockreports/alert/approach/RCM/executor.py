import pandas as pd
from scipy.signal import find_peaks
import logging
import json
from typing import Optional

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
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.common.regime import has_divergence
from .settings import RcmSettings


class RcmExecutor(Executor):
    APPROACH_NAME = Approach.RCM

    def __init__(self, symbol: str):
        self.settings = RcmSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the RCM approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_rcm_alerts(df, new_candle_count)
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

    def _find_rcm_alerts(self, df: pd.DataFrame, new_candle_count=0) -> list[AlertData]:
        """
        Finds alerts using the Reversal-Confirmation-Magnitude (RCM) approach.
        """
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        confirmation_window = self.settings.confirmation_window
        required_lookback = confirmation_window + 1

        df = prepare_indicators(df)
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        peak_trough_prominence = self.settings.peak_trough_prominence
        
        peaks, _ = find_peaks(df['close'], prominence=peak_trough_prominence)
        troughs, _ = find_peaks(-df['close'], prominence=peak_trough_prominence)
        
        reversal_points = {
            'peak': {idx: True for idx in peaks},
            'trough': {idx: True for idx in troughs}
        }

        min_consistency = self.settings.confirmation_min_consistency
        lookback_period = self.settings.peak_bottom_lookback_period
        min_magnitude = self.settings.min_alert_magnitude

        if len(df) < required_lookback:
            return alerts

        df_indexed = df.reset_index()

        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            current_candle = df_indexed.iloc[i]
            prev_candle = df_indexed.iloc[i-1]

            for j in range(1, confirmation_window + 1):
                reversal_idx = i - j
                if reversal_idx < 0:
                    break

                reversal_candle = df_indexed.iloc[reversal_idx]
                is_peak = reversal_points['peak'].get(reversal_idx, False)
                is_trough = reversal_points['trough'].get(reversal_idx, False)

                if not (is_peak or is_trough):
                    continue

                confirmation_df = df.iloc[reversal_idx + 1 : i + 1].copy()
                
                signal: Optional[Signal] = None
                if is_trough:
                    if (confirmation_df['close'] > confirmation_df['open']).sum() >= min_consistency:
                        signal = Signal.BUY
                elif is_peak:
                    if (confirmation_df['close'] < confirmation_df['open']).sum() >= min_consistency:
                        signal = Signal.SELL

                if not signal:
                    continue

                if not _is_rsi_not_exhausted([current_candle], signal, self.settings):
                    continue

                if not is_signal_confirmed(current_candle, signal, self.settings):
                    continue

                if lookback_period is not None:
                    lookback_start_idx = max(0, reversal_idx - lookback_period)
                    lookback_df = df_indexed.iloc[lookback_start_idx:reversal_idx]
                    if not lookback_df.empty:
                        if signal == Signal.BUY and current_candle['close'] <= lookback_df['high'].max():
                            continue
                        if signal == Signal.SELL and current_candle['close'] >= lookback_df['low'].min():
                            continue
                
                reversal_price = reversal_candle['close']
                is_sufficient, magnitude = check_magnitude(current_candle['close'], reversal_price, min_magnitude)
                if not is_sufficient:
                    continue

                use_volume_spike = self.settings.use_volume_confirmation
                use_increasing_volume = self.settings.use_volume_increasing_confirmation
                use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

                volume_spike_ok = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
                volume_increasing_ok = not use_increasing_volume or is_volume_increasing(confirmation_df)
                last_candle_max_volume_ok = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)
                if not (volume_spike_ok and volume_increasing_ok and last_candle_max_volume_ok):
                    continue

                alert_time = current_candle['time']
                reversal_time = reversal_candle['time']
                if isinstance(reversal_time, pd.Timestamp):
                    reversal_time = reversal_time.isoformat()
                alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

                alert_data = AlertData(
                    approach=self.APPROACH_NAME,
                    id=alert_id,
                    symbol=self.symbol,
                    signal=signal,
                    alert_price=current_candle['close'],
                    alert_time=alert_time,
                    start_price=reversal_price,
                    start_time=reversal_time,
                    magnitude=magnitude,
                    details=json.dumps({
                        "peak_trough_prominence": peak_trough_prominence,
                        "confirmation_window": confirmation_window,
                        "peak_bottom_lookback_period": lookback_period
                    })
                )
                alerts.append(alert_data)

                if not is_development_mode:
                    return alerts
                
                break 
        
        return alerts[::-1]
