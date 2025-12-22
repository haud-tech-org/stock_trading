import pandas as pd
import logging
import json
import numpy as np
from typing import Optional, Dict, Any, List

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, can_apply_volume_confirmation
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators, 
    _is_rsi_not_exhausted,
    is_signal_confirmed
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from .settings import MomentumExhaustionSettings


class MomentumExhaustionExecutor(Executor):
    APPROACH_NAME = Approach.MOMENTUM_EXHAUSTION

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = MomentumExhaustionSettings(symbol)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the MOMENTUM_EXHAUSTION approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_momentum_exhaustion_alerts(df, new_candle_count)
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

    def _analyze_window(self, window: pd.DataFrame, df_indexed: pd.DataFrame) -> Optional[AlertData]:
        """
        Analyzes a single window of data to find a momentum exhaustion alert.
        """
        momentum_count = self.settings.momentum_candle_count
        exhaustion_count = self.settings.exhaustion_candle_count
        use_volume = self.settings.use_volume_confirmation
        total_pattern_candles = momentum_count + exhaustion_count

        confirmation_candle = window.iloc[-1]
        reversal_candle = window.iloc[-2]
        exhaustion_candles = window.iloc[-(exhaustion_count + 2):-2]
        momentum_candles = window.iloc[-(total_pattern_candles + 2):-(exhaustion_count + 2)]
        
        start_loc = df_indexed.index.get_loc(window.index[0])
        
        required_past_data = momentum_count - 1
        sma_start_loc = max(0, start_loc - required_past_data)
        sma_end_loc = start_loc + momentum_count
        sma_data_slice = df_indexed.iloc[sma_start_loc:sma_end_loc]

        sma = sma_data_slice['close'].rolling(window=momentum_count).mean()
        trend_sma = sma.tail(momentum_count)

        if trend_sma.isnull().any() or len(trend_sma) < 2:
            return None

        x = range(len(trend_sma))
        y = trend_sma.values
        slope = np.polyfit(x, y, 1)[0]

        slope_threshold = self.settings.sma_slope_threshold 

        is_bullish_trend = slope > slope_threshold
        is_bearish_trend = slope < -slope_threshold

        if not (is_bullish_trend or is_bearish_trend):
            return None

        signal: Optional[Signal] = None
        if is_bullish_trend and reversal_candle['close'] < reversal_candle['open']:
            if confirmation_candle['close'] < confirmation_candle['open']:
                signal = Signal.SELL
        elif is_bearish_trend and reversal_candle['close'] > reversal_candle['open']:
            if confirmation_candle['close'] > confirmation_candle['open']:
                signal = Signal.BUY
        
        if not signal:
            return None

        window['body'] = abs(window['close'] - window['open'])
        
        avg_momentum_body = window.loc[momentum_candles.index, 'body'].mean()
        avg_exhaustion_body = window.loc[exhaustion_candles.index, 'body'].mean()

        if avg_exhaustion_body >= avg_momentum_body:
            return None

        reversal_candle_body = window.loc[reversal_candle.name, 'body']
        if reversal_candle_body <= avg_exhaustion_body:
            return None

        if use_volume:
            avg_momentum_volume = window.loc[momentum_candles.index, 'volume'].mean()
            avg_exhaustion_volume = window.loc[exhaustion_candles.index, 'volume'].mean()
            if avg_exhaustion_volume >= avg_momentum_volume:
                return None
                
            reversal_candle_index = df_indexed.index.get_loc(reversal_candle.name)
            if not (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), reversal_candle_index)):
                return None

        self.logger.info(f"[{reversal_candle.name}] SUCCESS: Momentum Exhaustion Pattern Found! Signal: {signal}")
        start_candle = momentum_candles.iloc[0]
        
        alert_time = confirmation_candle.name
        current_price = confirmation_candle['close']
        start_price = start_candle['open']

        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
        start_time_ts = int(start_candle.name.tz_convert('UTC').timestamp())

        start_time = start_candle.name
        if isinstance(start_time, pd.Timestamp):
            start_time = start_time.isoformat()
        alert_data = AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=current_price,
            alert_time=alert_time,
            start_price=start_price,
            start_time=start_time,
            magnitude=round(abs(current_price - start_price), 2),
            details=json.dumps({
                "reason": "Reversal after momentum exhaustion detected.",
                "pattern_start_time": start_time_ts,
                "avg_momentum_body": round(avg_momentum_body, 2),
                "avg_exhaustion_body": round(avg_exhaustion_body, 2)
            })
        )
        return alert_data

    def _find_momentum_exhaustion_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Finds alerts based on a momentum exhaustion pattern using a unified reverse loop.
        """
        alerts = []
        momentum_count = self.settings.momentum_candle_count
        exhaustion_count = self.settings.exhaustion_candle_count
        required_lookback = momentum_count + exhaustion_count + 2
        
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT

        df = prepare_indicators(df)
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        df_indexed = df.set_index('time')

        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            window = df_indexed.iloc[i - required_lookback + 1 : i + 1].copy()
            
            alert = self._analyze_window(window, df_indexed)
            
            if alert:
                confirmation_candle = df_indexed.iloc[i]

                candles_for_exhaustion_check = [confirmation_candle]
                if not _is_rsi_not_exhausted(candles_for_exhaustion_check, alert.signal, self.settings.approach_settings):
                    continue

                if not is_signal_confirmed(confirmation_candle, alert.signal, self.settings.approach_settings):
                    continue

                alerts.append(alert)
                if not is_development_mode:
                    return alerts

        return alerts[::-1]
