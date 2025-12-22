import pandas as pd
import logging
import json
from typing import Optional, Tuple
import numpy as np
from scipy.signal import find_peaks

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.data_utils import can_apply_analysis
from .settings import VolumeSpikeConfirmationSettings

logger = logging.getLogger(__name__)

class VolumeSpikeConfirmationExecutor(Executor):
    APPROACH_NAME = Approach.VOLUME_SPIKE_CONFIRMATION
    LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None

    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol)
        self.settings = VolumeSpikeConfirmationSettings(symbol)
        self.logger = logging.getLogger(__name__)
        self.debug = debug

    def run(self, df: pd.DataFrame, new_candle_count: int) -> AlertResult:
        try:
            df.columns = [col.lower() for col in df.columns]
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")

            alerts_data = self._find_volume_spike_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame(), status="FAILED", message=str(e))

    def _find_volume_spike_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        # --- 1. Initial Data Sufficiency Checks ---
        if len(df) < self.settings.min_lookback_data:
            self.logger.warning(f"{self.APPROACH_NAME}: Insufficient data for reliable volume average. Required: {self.settings.min_lookback_data}, have: {len(df)}.")
            return alerts

        required_lookback = 1 + self.settings.signal_lookback_period
        if not can_apply_analysis(df, required_rows=required_lookback, approach_name=self.APPROACH_NAME):
            self.logger.warning(f"{self.APPROACH_NAME}: Insufficient data for pattern analysis. Required: {required_lookback}, have: {len(df)}.")
            return alerts

        df_indexed = df.set_index('time')

        # --- 2. Setup Reverse Loop ---
        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            # --- 3. Identify Signal and Confirmation Candles ---
            lookback_start_index = i - self.settings.signal_lookback_period + 1
            lookback_end_index = i + 1
            signal_candle_window = df_indexed.iloc[lookback_start_index:lookback_end_index]
            if signal_candle_window.empty:
                continue

            # Condition 1: The lookback window must be larger than 2
            if len(signal_candle_window) <= 2:
                if self.debug:
                    self.logger.info(f"[{signal_candle_window.index[-1]}] Lookback window too small (size={len(signal_candle_window)}). Skipping.")
                continue
            
            # The signal candle is the one with max volume in the window (excluding the confirmation candle)
            signal_candle = signal_candle_window.iloc[:-1].loc[signal_candle_window.iloc[:-1]['volume'].idxmax()]
            
            # Condition: signal_candle must be inside the window (not first or last)
            signal_candle_pos = signal_candle_window.iloc[:-1].index.get_loc(signal_candle.name)
            if signal_candle_pos == 0 or signal_candle_pos == len(signal_candle_window.iloc[:-1]) - 1:
                if self.debug:
                    self.logger.info(f"[{signal_candle.name}] Signal candle is at window edge (idx={signal_candle_pos}). Skipping.")
                continue

            # --- 4. Volume Spike Condition ---
            signal_candle_index = df_indexed.index.get_loc(signal_candle.name)
            intraday_df = df_indexed.iloc[:signal_candle_index]
            if intraday_df.empty:
                continue

            avg_volume = intraday_df['volume'].mean()
            if signal_candle['volume'] < avg_volume * self.settings.volume_spike_multiplier:
                continue

            # --- 5. Confirmation Candle Shape Condition ---
            confirmation_candle = signal_candle_window.iloc[-1]
            confirmation_body = abs(confirmation_candle['close'] - confirmation_candle['open'])
            confirmation_range = confirmation_candle['high'] - confirmation_candle['low']
            
            if confirmation_body < self.settings.min_confirmation_body_size:
                continue
            
            if confirmation_range > 0:
                body_ratio = confirmation_body / confirmation_range
                if body_ratio < self.settings.min_confirmation_body_ratio:
                    continue
            elif self.settings.min_confirmation_body_ratio > 0:
                continue

            # --- 6. Peak/Trough, Trend, and Confirmation Logic ---
            potential_signal = None
            if confirmation_candle['close'] > confirmation_candle['open']:
                potential_signal = Signal.BUY
            elif confirmation_candle['close'] < confirmation_candle['open']:
                potential_signal = Signal.SELL
            else:
                continue

            # --- 6a. Combined Signal Validation ---
            signal = None
            pre_spike_window = signal_candle_window.loc[:signal_candle.name].iloc[:-1]
            if pre_spike_window.empty:
                continue

            prominence = self.settings.peak_trough_prominence

            reversal_candle_idx = None
            if potential_signal == Signal.BUY:
                trough_indices, _ = find_peaks(-signal_candle_window['close'], prominence=prominence)
                if trough_indices.size == 0: continue
                reversal_candle_idx = trough_indices[np.argmin(signal_candle_window['close'].iloc[trough_indices])]
                is_pre_spike_trend_valid = (pre_spike_window['close'] < pre_spike_window['open']).all()
                if is_pre_spike_trend_valid:
                    signal = Signal.BUY
            elif potential_signal == Signal.SELL:
                peak_indices, _ = find_peaks(signal_candle_window['close'], prominence=prominence)
                if peak_indices.size == 0: continue
                reversal_candle_idx = peak_indices[np.argmax(signal_candle_window['close'].iloc[peak_indices])]
                is_pre_spike_trend_valid = (pre_spike_window['close'] > pre_spike_window['open']).all()
                if is_pre_spike_trend_valid:
                    signal = Signal.SELL
            # Condition 2: reversal_candle must not be first or last in window
            if reversal_candle_idx is not None and (reversal_candle_idx == 0 or reversal_candle_idx == len(signal_candle_window) - 1):
                if self.debug:
                    self.logger.info(f"[{confirmation_candle.name}] Reversal candle is at window edge (idx={reversal_candle_idx}). Skipping.")
                continue

            if signal:
                # --- 8. Cooldown Condition ---
                if VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP is not None:
                    time_since_last_alert = confirmation_candle.name - VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP
                    if time_since_last_alert.total_seconds() / 60 < self.settings.cooldown_period:
                        continue

                # --- 9. Generate Alert ---
                alert = self._create_alert(confirmation_candle, signal_candle, signal, signal_candle_window)
                alerts.append(alert)
                VolumeSpikeConfirmationExecutor.LATEST_ALERT_TIMESTAMP = alert.alert_time
                if not is_development_mode:
                    return alerts
        
        return alerts[::-1]

    def _create_alert(self, alert_candle: pd.Series, signal_candle: pd.Series, signal: str, signal_candle_window: pd.DataFrame) -> AlertData:
        alert_time = alert_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        details = {
            "signal_candle_time": signal_candle.name.isoformat(),
            "signal_candle_volume": float(signal_candle['volume']),
            "confirmation_body_size": float(abs(alert_candle['close'] - alert_candle['open'])),
            "window_start_time": signal_candle_window.index[0].isoformat(),
            "window_start_close": float(signal_candle_window.iloc[0]['close']),
            "window_end_time": signal_candle_window.index[-1].isoformat(),
            "window_end_close": float(signal_candle_window.iloc[-1]['close'])
        }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=alert_candle['close'],
            alert_time=alert_time,
            start_price=signal_candle_window.iloc[0]['close'],
            start_time=signal_candle_window.index[0],
            magnitude=round(abs(alert_candle['close'] - signal_candle['close']), 2),
            details=json.dumps(details)
        )
