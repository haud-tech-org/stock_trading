import pandas as pd
import logging
import json
import numpy as np
from typing import Optional

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, is_signal_confirmed, _is_rsi_not_exhausted
from src.stockreports.alert.common.data_utils import can_apply_analysis

class ConsecutivePowerCandlesExecutor(Executor):
    APPROACH_NAME = Approach.CONSECUTIVE_POWER_CANDLES

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = loader.get_settings()
        self.signal_settings = loader.get_signal_settings()
        self.logger = logging.getLogger(__name__)
        self.CONFIG = self.signal_settings.APPROACH_CONFIG.get(
            self.APPROACH_NAME, self.signal_settings.APPROACH_CONFIG.get("default", {})
        )

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the CONSECUTIVE_POWER_CANDLES approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")

            alerts_data = self._find_power_candle_alerts(df, new_candle_count)
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
        Analyzes a window for a configurable number of consecutive power candles.
        """
        candle_count = self.CONFIG.get("CANDLE_COUNT", 3)
        min_body_ratio = self.CONFIG.get("MIN_BODY_TO_RANGE_RATIO", 0.7)
        use_volume = self.CONFIG.get("USE_VOLUME_CONFIRMATION", False)
        use_last_candle_max_volume = self.CONFIG.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        min_pre_candle_body_sizes = self.CONFIG.get("MIN_PRE_CANDLE_BODY_SIZES", [])

        if len(window) != candle_count:
            return None

        is_all_bullish = all(window['close'] > window['open'])
        is_all_bearish = all(window['close'] < window['open'])

        if not (is_all_bullish or is_all_bearish):
            return None

        signal = Signal.BUY if is_all_bullish else Signal.SELL

        window['body'] = abs(window['close'] - window['open'])
        window['range'] = window['high'] - window['low']
        window['avg_body_price'] = (window['open'] + window['close']) / 2

        window_body_ratio = (window['body'] / window['range']).fillna(0)
        if not all(window_body_ratio >= min_body_ratio):
            return None

        pre_candles = window.iloc[:-1]
        
        if len(min_pre_candle_body_sizes) != len(pre_candles):
            self.logger.warning(f"Config mismatch: CANDLE_COUNT is {candle_count}, but MIN_PRE_CANDLE_BODY_SIZES has {len(min_pre_candle_body_sizes)} entries. Skipping.")
            return None

        for i, min_size in enumerate(min_pre_candle_body_sizes):
            if pre_candles.iloc[i]['body'] < min_size:
                return None

        for i in range(1, len(window)):
            current_candle = window.iloc[i]
            prev_candle = window.iloc[i-1]
            
            if is_all_bullish:
                if not (current_candle['open'] > prev_candle['avg_body_price']):
                    return None
            elif is_all_bearish:
                if not (current_candle['open'] < prev_candle['avg_body_price']):
                    return None

        last_candle = window.iloc[-1]
        if use_volume:
            last_candle_index = df_indexed.index.get_loc(last_candle.name)
            if not (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), last_candle_index)):
                return None

        if use_last_candle_max_volume:
            if not is_last_candle_volume_max(window):
                return None

        first_candle_index = df_indexed.index.get_loc(window.iloc[0].name)
        setup_candle = df_indexed.iloc[first_candle_index - 1] if first_candle_index > 0 else None
        
        if self.CONFIG.get("USE_RSI_EXHAUSTION_FILTER", False):
            candles_for_exhaustion_check = [setup_candle] if setup_candle is not None else []
            if not _is_rsi_not_exhausted(candles_for_exhaustion_check, signal, self.CONFIG):
                return None

        final_candle = window.iloc[-1]
        if not is_signal_confirmed(final_candle, signal, self.CONFIG):
            return None

        self.logger.info(f"[{final_candle.name}] SUCCESS: Consecutive Power Candles Pattern Found! Signal: {signal}")

        alert_id = str(int(final_candle.name.tz_convert('UTC').timestamp()))
        start_candle = window.iloc[0]

        alert_data = AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=final_candle['close'],
            alert_time=final_candle.name,
            start_price=start_candle['open'],
            start_time=start_candle.name,
            magnitude=round(abs(final_candle['close'] - start_candle['open']), 2),
            details=json.dumps({
                "reason": f"{candle_count} consecutive power candles with body/open progression detected.",
                "pattern_start_time": int(start_candle.name.tz_convert('UTC').timestamp()),
                "last_candle_volume": final_candle['volume']
            })
        )
        return alert_data

    def _find_power_candle_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Finds alerts based on the consecutive power candles pattern.
        """
        alerts = []
        window_size = self.CONFIG.get("CANDLE_COUNT", 3)
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT

        df = prepare_indicators(df)

        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=window_size):
            return alerts

        df_indexed = df.set_index('time')

        loop_end = len(df_indexed) - 1
        loop_start = window_size - 1
        active_region_start = len(df_indexed) - new_candle_count - window_size

        for i in range(loop_end, loop_start - 1, -1):
            if i < active_region_start:
                break

            window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()
            
            alert = self._analyze_window(window, df_indexed)
            
            if alert:
                alerts.append(alert)
                if not is_development_mode:
                    return alerts

        return alerts[::-1]
