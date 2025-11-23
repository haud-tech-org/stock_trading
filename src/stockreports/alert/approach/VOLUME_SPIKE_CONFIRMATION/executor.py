import pandas as pd
import logging
import json
from typing import Optional, Tuple

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.data_utils import can_apply_analysis
from .settings import VolumeSpikeConfirmationSettings

logger = logging.getLogger(__name__)

class VolumeSpikeConfirmationExecutor(Executor):
    APPROACH_NAME = Approach.VOLUME_SPIKE_CONFIRMATION
    LATEST_ALERT_CONTEXT: Optional[Tuple[pd.Timestamp, str]] = None

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
        loop_start = required_lookback - 1
        active_region_start = len(df_indexed) - new_candle_count

        for i in range(loop_end, loop_start - 1, -1):
            if not is_development_mode and i < active_region_start:
                break

            # --- 3. Identify Signal and Confirmation Candles ---
            confirmation_candle = df_indexed.iloc[i]
            
            lookback_start_index = i - self.settings.signal_lookback_period
            lookback_end_index = i
            signal_candle_window = df_indexed.iloc[lookback_start_index:lookback_end_index]

            if signal_candle_window.empty:
                continue

            signal_candle = signal_candle_window.loc[signal_candle_window['volume'].idxmax()]
            
            # --- 4. Volume Spike Condition ---
            signal_candle_index = df_indexed.index.get_loc(signal_candle.name)
            intraday_df = df_indexed.iloc[:signal_candle_index]
            if intraday_df.empty:
                continue
            avg_volume = intraday_df['volume'].mean()
            
            if signal_candle['volume'] < avg_volume * self.settings.volume_spike_multiplier:
                continue

            # --- 5. Intermediate Trend Consistency ---
            # This window includes the signal candle and all candles up to (but not including) the confirmation candle.
            intermediate_candles = df_indexed.iloc[signal_candle_index : i]
            if not intermediate_candles.empty:
                is_all_green = (intermediate_candles['close'] > intermediate_candles['open']).all()
                is_all_red = (intermediate_candles['close'] < intermediate_candles['open']).all()
                if not (is_all_green or is_all_red):
                    continue # Fails if intermediate candles are mixed

            # --- 6. Confirmation Candle Shape Condition ---
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

            # --- 7. Signal Direction Condition ---
            signal = None
            if confirmation_candle['close'] > confirmation_candle['open'] and confirmation_candle['close'] > signal_candle['close']:
                signal = Signal.BUY
            elif confirmation_candle['close'] < confirmation_candle['open'] and confirmation_candle['close'] < signal_candle['close']:
                signal = Signal.SELL
            
            if signal:
                # --- 8. Cooldown Condition ---
                if VolumeSpikeConfirmationExecutor.LATEST_ALERT_CONTEXT is not None:
                    last_alert_time, last_signal = VolumeSpikeConfirmationExecutor.LATEST_ALERT_CONTEXT
                    if signal == last_signal:
                        time_since_last_alert = confirmation_candle.name - last_alert_time
                        if time_since_last_alert.total_seconds() / 60 < self.settings.cooldown_period:
                            continue

                # --- 9. Generate Alert ---
                alert = self._create_alert(confirmation_candle, signal_candle, signal)
                alerts.append(alert)
                
                VolumeSpikeConfirmationExecutor.LATEST_ALERT_CONTEXT = (alert.alert_time, alert.signal)
                
                if not is_development_mode:
                    return alerts
        
        return alerts[::-1]

    def _create_alert(self, alert_candle: pd.Series, signal_candle: pd.Series, signal: str) -> AlertData:
        alert_time = alert_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        details = {
            "signal_candle_time": signal_candle.name.isoformat(),
            "signal_candle_volume": signal_candle['volume'],
            "confirmation_body_size": abs(alert_candle['close'] - alert_candle['open']),
        }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=alert_candle['close'],
            alert_time=alert_time,
            start_price=signal_candle['close'],
            start_time=signal_candle.name,
            magnitude=round(abs(alert_candle['close'] - signal_candle['close']), 2),
            details=json.dumps(details)
        )
