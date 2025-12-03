import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks
import ta

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    is_signal_confirmed,
    _is_rsi_not_exhausted
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.common.volume import (
    is_volume_spike_confirmed, 
    can_apply_volume_confirmation, 
    is_last_candle_volume_max,
    is_volume_increasing
)
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.utils.time_utils import to_iso8601_with_tz
from .settings import ConsistentMomentumSettings


class ConsistentMomentumExecutor(Executor):
    APPROACH_NAME = Approach.CONSISTENT_MOMENTUM

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

    def _analyze_window(self, window: pd.DataFrame, df_indexed: pd.DataFrame, window_size: int) -> Optional[AlertData]:
        """
        Analyzes a single window of data to find a consistent momentum alert.
        """
        is_all_bullish = (window['close'] > window['open']).all()
        is_all_bearish = (window['close'] < window['open']).all()

        if not (is_all_bullish or is_all_bearish):
            return None

        window['avg_price'] = (window['high'] + window['low'] + window['close']) / 3
        
        is_momentum_confirmed = False
        if is_all_bullish:
            if (window['avg_price'].diff().dropna() >= 0).all():
                is_momentum_confirmed = True
                signal = Signal.BUY
        elif is_all_bearish:
            if (window['avg_price'].diff().dropna() <= 0).all():
                is_momentum_confirmed = True
                signal = Signal.SELL
        
        if not is_momentum_confirmed:
            return None

        current_candle = window.iloc[-1]
        candle_range = (current_candle['high'] - current_candle['low'])
        if candle_range == 0: return None

        strong_close_min, _ = self.settings.strong_close_threshold_range
        is_strong_close = False
        if signal == Signal.BUY and ((current_candle['close'] - current_candle['low']) / candle_range) >= strong_close_min:
            is_strong_close = True
        elif signal == Signal.SELL and ((current_candle['high'] - current_candle['close']) / candle_range) >= strong_close_min:
            is_strong_close = True

        if not is_strong_close:
            return None

        lookback_minutes = self.settings.peak_bottom_lookback_period
        prominence = self.settings.peak_trough_prominence
        momentum_start_time = window.index[0]
        
        if lookback_minutes is None:
            lookback_df = df_indexed.loc[:momentum_start_time].iloc[:-1]
        else:
            lookback_start_time = momentum_start_time - pd.Timedelta(minutes=lookback_minutes)
            lookback_df = df_indexed.loc[lookback_start_time:momentum_start_time].iloc[:-1]

        if lookback_df.empty:
            return None

        is_breakout_confirmed = False
        if signal == Signal.BUY:
            peaks, _ = find_peaks(lookback_df['high'], prominence=prominence)
            if peaks.size > 0:
                last_peak_index = peaks[-1]
                last_peak_high = lookback_df['high'].iloc[last_peak_index]
                if current_candle['close'] > last_peak_high:
                    is_breakout_confirmed = True
        elif signal == Signal.SELL:
            troughs, _ = find_peaks(-lookback_df['low'], prominence=prominence)
            if troughs.size > 0:
                last_trough_index = troughs[-1]
                last_trough_low = lookback_df['low'].iloc[last_trough_index]
                if current_candle['close'] < last_trough_low:
                    is_breakout_confirmed = True

        if not is_breakout_confirmed:
            return None

        use_volume_spike = self.settings.use_volume_confirmation
        use_increasing_volume = self.settings.use_volume_increasing_confirmation
        use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

        confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
        confirmation_df = df_indexed.iloc[confirmation_candle_index - window_size + 1 : confirmation_candle_index + 1]

        volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), confirmation_candle_index))
        volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)

        if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
            return None

        body_to_range_min_ratio = self.settings.body_to_range_min_ratio
        current_candle_body = abs(current_candle['close'] - current_candle['open'])
        current_candle_range = current_candle['high'] - current_candle['low']

        if current_candle_range > 0:
            body_ratio = current_candle_body / current_candle_range
            if body_ratio < body_to_range_min_ratio:
                return None
        else:
            if body_to_range_min_ratio > 0:
                return None

        window['body'] = abs(window['close'] - window['open'])
        window['range'] = window['high'] - window['low']
        window['wick'] = window['range'] - window['body']
        
        total_body = window['body'].sum()
        total_wick = window['wick'].sum()

        if total_body <= total_wick:
            return None

        start_candle = window.iloc[0]
        end_candle = window.iloc[-1]
        candles_for_rsi_check = [start_candle, end_candle]
        
        if not _is_rsi_not_exhausted(candles_for_rsi_check, signal, self.settings):
            return None

        if not is_signal_confirmed(end_candle, signal, self.settings):
            return None

        start_candle = window.iloc[0]
        
        alert_time = current_candle.name
        momentum_start_time = start_candle.name
        current_price = current_candle['close']
        momentum_start_price = start_candle['open']

        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        start_time = to_iso8601_with_tz(momentum_start_time)
        momentum_start_time_iso = to_iso8601_with_tz(momentum_start_time)

        alert_data = AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=current_price,
            alert_time=alert_time,
            start_price=momentum_start_price,
            start_time=start_time,
            magnitude=round(abs(current_price - momentum_start_price), 2),
            details=json.dumps({
                "reason": "Consistent Momentum with Breakout",
                "momentum_start_time": momentum_start_time_iso,
                "momentum_window_size": window_size,
                "breakout_lookback_minutes": lookback_minutes
            })
        )
        return alert_data

    def _is_immediate_reversal(self, candle: pd.Series, original_signal: Signal) -> bool:
        """
        Checks if the given candle is a strong reversal compared to the original signal.
        """
        reversal_ratio = self.settings.reversal_candle_body_ratio
        
        candle_range = candle['high'] - candle['low']
        if candle_range == 0:
            return False

        body_size = abs(candle['close'] - candle['open'])
        
        if original_signal == Signal.BUY and candle['close'] < candle['open']:
            if (body_size / candle_range) >= reversal_ratio:
                return True
        elif original_signal == Signal.SELL and candle['close'] > candle['open']:
            if (body_size / candle_range) >= reversal_ratio:
                return True

        return False

    def _find_consistent_momentum_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Finds alerts based on a consistent momentum pattern using a unified reverse loop.
        """
        alerts = []
        window_size = self.settings.window_size
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        if window_size < 2:
            self.logger.error(f"{self.APPROACH_NAME}: 'CONFIRMATION_WINDOW' must be at least 2. Aborting.")
            return alerts

        required_lookback = window_size
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        df_indexed = df.set_index('time')

        loop_end = len(df_indexed) - 1
        loop_start = required_lookback - 1
        active_region_start = len(df_indexed) - new_candle_count - required_lookback

        for i in range(loop_end, loop_start - 1, -1):
            if i < active_region_start:
                break

            window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()
            
            alert = self._analyze_window(window, df_indexed, window_size)
            
            if alert:
                if self.settings.use_realtime_reversal_confirmation:
                    confirmation_window_size = self.settings.realtime_reversal_confirmation_window
                    if i + confirmation_window_size < len(df_indexed):
                        confirmation_window = df_indexed.iloc[i + 1 : i + 1 + confirmation_window_size]
                        is_reversal = False
                        for _, candle in confirmation_window.iterrows():
                            if self._is_immediate_reversal(candle, alert.signal):
                                is_reversal = True
                                break
                        if is_reversal:
                            alert = None
                
                if alert:
                    alerts.append(alert)
                    if not is_development_mode:
                        return alerts

        return alerts[::-1]
