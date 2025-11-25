# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/executor.py

import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks
import numpy as np

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, is_signal_confirmed
from src.stockreports.alert.common.data_utils import can_apply_analysis


class ConsolidationBreakoutExecutor(Executor):
    APPROACH_NAME = Approach.CONSOLIDATION_BREAKOUT

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
        Entry point for the CONSOLIDATION_BREAKOUT approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_consolidation_breakout_alerts(df, new_candle_count)
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

    def _find_consolidation_breakout_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        """
        Finds alerts by iterating through a range of lookback periods.
        """
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT

        lookback_values = self.CONFIG.get("CONSOLIDATION_LOOKBACK", [50])
        if not isinstance(lookback_values, list):
            lookback_values = [lookback_values]

        min_lookback, max_lookback = min(lookback_values), max(lookback_values)
        required_lookback = max_lookback + self.CONFIG.get("BREAKOUT_CONFIRMATION_CANDLES", 1)

        df = prepare_indicators(df)
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        df_indexed = df.set_index('time')

        loop_end = len(df_indexed) - 1
        loop_start = required_lookback - 1
        
        active_region_start = len(df_indexed) - new_candle_count if not is_development_mode else loop_start

        for i in range(loop_end, loop_start - 1, -1):
            if not is_development_mode and i < active_region_start:
                break

            for lookback in range(min_lookback, max_lookback + 1):
                current_required_lookback = lookback + self.CONFIG.get("BREAKOUT_CONFIRMATION_CANDLES", 1)
                if i < current_required_lookback - 1:
                    continue

                window = df_indexed.iloc[i - current_required_lookback + 1 : i + 1].copy()
                
                alert = self._analyze_window(window, lookback)
                
                if alert:
                    alerts.append(alert)
                    if not is_development_mode:
                        return alerts
                    break 

        return alerts[::-1]

    def _analyze_window(self, window: pd.DataFrame, lookback: int) -> Optional[AlertData]:
        """
        Analyzes a single window of data to find a consolidation breakout pattern for a specific lookback.
        """
        consolidation_window = window.iloc[:lookback]
        breakout_window = window.iloc[lookback:]

        center_price = consolidation_window['close'].median()
        max_deviation = self.CONFIG.get("MAX_DEVIATION_FROM_CENTER")
        is_clustered = (consolidation_window['close'] >= center_price - max_deviation) & \
                       (consolidation_window['close'] <= center_price + max_deviation)
        
        min_ratio = self.CONFIG.get("MIN_CLUSTERED_CANDLE_RATIO")
        if is_clustered.mean() < min_ratio:
            self.logger.debug(f"Window ending {window.index[-1]}: Failed MIN_CLUSTERED_CANDLE_RATIO. "
                            f"Got {is_clustered.mean():.2f}, need {min_ratio}.")
            return None

        if self.CONFIG.get("USE_CHANNEL_CONSISTENCY_CHECK", False):
            core_channel_df = consolidation_window[is_clustered]
            core_resistance = core_channel_df['high'].max()
            core_support = core_channel_df['low'].min()
            
            outliers = (consolidation_window['close'] > core_resistance) | \
                       (consolidation_window['close'] < core_support)
            
            max_outlier_ratio = self.CONFIG.get("MAX_CHANNEL_OUTLIER_RATIO", 0.1)
            
            if outliers.sum() / lookback > max_outlier_ratio:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_CHANNEL_OUTLIER_RATIO. "
                                f"Got {outliers.sum() / lookback:.2f}, max {max_outlier_ratio}.")
                return None

        if self.CONFIG.get("USE_BALANCED_SIDEWAYS_CHECK", False):
            max_slope = self.CONFIG.get("MAX_REGRESSION_SLOPE", 0.05)
            x = np.arange(len(consolidation_window))
            y = consolidation_window['close'].values
            slope, _ = np.polyfit(x, y, 1)
            if abs(slope) > max_slope:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_REGRESSION_SLOPE. "
                                f"Got {abs(slope):.4f}, max {max_slope}.")
                return None

            max_balance_deviation = self.CONFIG.get("MAX_TIME_BALANCE_DEVIATION_RATIO", 0.3)
            candles_above = (consolidation_window['close'] > center_price).sum()
            candles_below = (consolidation_window['close'] < center_price).sum()
            balance_ratio = abs(candles_above - candles_below) / lookback
            if balance_ratio > max_balance_deviation:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_TIME_BALANCE_DEVIATION_RATIO. "
                                f"Got {balance_ratio:.2f}, max {max_balance_deviation}.")
                return None

        if self.CONFIG.get("USE_CONSECUTIVE_TREND_CHECK", False):
            max_consecutive = self.CONFIG.get("MAX_CONSECUTIVE_TREND_CANDLES", 7)
            
            direction = np.sign(consolidation_window['close'] - consolidation_window['open'])
            
            longest_run = 0
            current_run = 0
            for i in range(1, len(direction)):
                if direction.iloc[i] != 0 and direction.iloc[i] == direction.iloc[i-1]:
                    current_run += 1
                else:
                    longest_run = max(longest_run, current_run)
                    current_run = 1 if direction.iloc[i] != 0 else 0
            longest_run = max(longest_run, current_run)

            if longest_run > max_consecutive:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_CONSECUTIVE_TREND_CANDLES. "
                                f"Got {longest_run}, max {max_consecutive}.")
                return None

        min_peaks_troughs = self.CONFIG.get("MIN_PEAKS_TROUGHS", 0)
        if min_peaks_troughs > 0:
            prominence = self.CONFIG.get("PEAK_TROUGH_PROMINENCE", None)
            peak_indices, _ = find_peaks(consolidation_window['high'], prominence=prominence)
            trough_indices, _ = find_peaks(-consolidation_window['low'], prominence=prominence)

            valid_peaks = [p for p in peak_indices if consolidation_window['high'].iloc[p] > center_price]
            valid_troughs = [t for t in trough_indices if consolidation_window['low'].iloc[t] < center_price]
            
            if len(valid_peaks) + len(valid_troughs) < min_peaks_troughs:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MIN_PEAKS_TROUGHS. "
                                f"Got {len(valid_peaks) + len(valid_troughs)}, min {min_peaks_troughs}.")
                return None

            if self.CONFIG.get("USE_ALTERNATING_PEAKS_TROUGHS_CHECK", False):
                points = [(i, 'peak') for i in valid_peaks] + [(i, 'trough') for i in valid_troughs]
                points.sort(key=lambda x: x[0])

                if len(points) > 1:
                    is_alternating = all(points[i][1] != points[i+1][1] for i in range(len(points) - 1))
                    if not is_alternating:
                        self.logger.debug(f"Window ending {window.index[-1]}: Failed USE_ALTERNATING_PEAKS_TROUGHS_CHECK.")
                        return None

        if self.CONFIG.get("USE_ADX_FILTER", False):
            adx_threshold = self.CONFIG.get("ADX_THRESHOLD")
            min_non_trending_ratio = self.CONFIG.get("ADX_CONFIRMATION_RATIO", 0.8)
            
            is_non_trending = consolidation_window['adx'] < adx_threshold
            
            if is_non_trending.mean() < min_non_trending_ratio:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed ADX_CONFIRMATION_RATIO. "
                                f"Got {is_non_trending.mean():.2f}, min {min_non_trending_ratio}.")
                return None

        if self.CONFIG.get("USE_BB_WIDTH_FILTER", False):
            bb_width_threshold = self.CONFIG.get("BB_WIDTH_THRESHOLD_PERCENT") / 100
            bb_width_percent = consolidation_window['bb_width'] / consolidation_window['bb_middle']
            is_squeezed = bb_width_percent < bb_width_threshold
            
            min_squeeze_ratio = self.CONFIG.get("BB_SQUEEZE_CONFIRMATION_RATIO", 0.8)
            if is_squeezed.mean() < min_squeeze_ratio:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed BB_SQUEEZE_CONFIRMATION_RATIO. "
                                f"Got {is_squeezed.mean():.2f}, min {min_squeeze_ratio}.")
                return None

        clustered_df = consolidation_window[is_clustered]
        resistance = clustered_df['high'].max()
        support = clustered_df['low'].min()

        breakout_candle = breakout_window.iloc[0]
        
        breakout_up = breakout_candle['close'] > resistance
        breakout_down = breakout_candle['close'] < support

        signal = None
        if breakout_up:
            signal = Signal.BUY
        elif breakout_down:
            signal = Signal.SELL
        else:
            self.logger.debug(f"Window ending {window.index[-1]}: No breakout. Price {breakout_candle['close']:.2f} "
                            f"is within channel ({support:.2f} - {resistance:.2f}).")
            return None

        last_consolidation_candle = consolidation_window.iloc[-1]
        if signal == Signal.BUY and last_consolidation_candle['close'] <= last_consolidation_candle['open']:
            self.logger.debug(f"Window ending {window.index[-1]}: Failed pre-breakout candle check for BUY. Last candle was bearish.")
            return None
        elif signal == Signal.SELL and last_consolidation_candle['close'] >= last_consolidation_candle['open']:
            self.logger.debug(f"Window ending {window.index[-1]}: Failed pre-breakout candle check for SELL. Last candle was bullish.")
            return None

        if self.CONFIG.get("USE_VOLUME_SPIKE_CONFIRMATION", False):
            avg_consolidation_volume = consolidation_window['volume'].mean()
            volume_multiplier = self.CONFIG.get("VOLUME_SPIKE_MULTIPLIER", 1.5)
            
            breakout_volume_spike = breakout_candle['volume'] >= avg_consolidation_volume * volume_multiplier
            last_candle_volume_spike = last_consolidation_candle['volume'] >= avg_consolidation_volume * volume_multiplier
            
            if not (breakout_volume_spike or last_candle_volume_spike):
                self.logger.debug(f"Window ending {window.index[-1]}: Failed USE_VOLUME_SPIKE_CONFIRMATION. "
                                f"Breakout volume: {breakout_candle['volume']:.0f}, "
                                f"Last candle volume: {last_consolidation_candle['volume']:.0f}, "
                                f"Avg volume: {avg_consolidation_volume:.0f}, "
                                f"Multiplier: {volume_multiplier}.")
                return None

        if self.CONFIG.get("USE_CONFIRMATION", False):
            if not is_signal_confirmed(breakout_candle, signal, self.CONFIG):
                self.logger.debug(f"Window ending {window.index[-1]}: Failed final signal confirmation (is_signal_confirmed).")
                return None

        self.logger.debug(f"Window ending {window.index[-1]}: All checks passed. Generating alert.")
        return self._create_alert(window, signal, resistance, support, lookback, is_clustered, breakout_candle)

    def _create_alert(self, window: pd.DataFrame, signal: Signal, resistance: float, support: float, lookback: int, is_clustered: pd.Series, breakout_candle: pd.Series) -> AlertData:
        """
        Creates and returns a standardized AlertData object.
        """
        start_candle = window.iloc[0]
        
        alert_time = breakout_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        details = {
            "reason": f"Price broke out of a {lookback}-candle consolidation channel.",
            "consolidation_resistance": resistance,
            "consolidation_support": support,
            "breakout_candle_close": breakout_candle['close'],
            "breakout_candle_volume": breakout_candle['volume'],
            "clustered_ratio": round(is_clustered.mean(), 2)
        }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=breakout_candle['close'],
            alert_time=alert_time,
            start_price=start_candle['open'],
            start_time=start_candle.name,
            magnitude=round(abs(breakout_candle['close'] - start_candle['open']), 2),
            details=json.dumps(details)
        )
