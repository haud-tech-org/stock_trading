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
from .settings import ConsolidationBreakoutSettings


class ConsolidationBreakoutExecutor(Executor):
    APPROACH_NAME = Approach.CONSOLIDATION_BREAKOUT

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = ConsolidationBreakoutSettings(symbol)
        self.logger = logging.getLogger(__name__)

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

        lookback_values = self.settings.consolidation_lookback
        min_lookback, max_lookback = min(lookback_values), max(lookback_values)
        required_lookback = max_lookback + self.settings.breakout_confirmation_candles

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
                current_required_lookback = lookback + self.settings.breakout_confirmation_candles
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
        max_deviation = self.settings.max_deviation_from_center
        is_clustered = (consolidation_window['close'] >= center_price - max_deviation) & \
                       (consolidation_window['close'] <= center_price + max_deviation)
        
        min_ratio = self.settings.min_clustered_candle_ratio
        if is_clustered.mean() < min_ratio:
            self.logger.debug(f"Window ending {window.index[-1]}: Failed MIN_CLUSTERED_CANDLE_RATIO. "
                            f"Got {is_clustered.mean():.2f}, need {min_ratio}.")
            return None

        if self.settings.use_channel_consistency_check:
            core_channel_df = consolidation_window[is_clustered]
            core_resistance = core_channel_df['high'].max()
            core_support = core_channel_df['low'].min()
            
            outliers = (consolidation_window['close'] > core_resistance) | \
                       (consolidation_window['close'] < core_support)
            
            max_outlier_ratio = self.settings.max_channel_outlier_ratio
            
            if outliers.sum() / lookback > max_outlier_ratio:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_CHANNEL_OUTLIER_RATIO. "
                                f"Got {outliers.sum() / lookback:.2f}, max {max_outlier_ratio}.")
                return None

        if self.settings.use_balanced_sideways_check:
            max_slope = self.settings.max_regression_slope
            x = np.arange(len(consolidation_window))
            y = consolidation_window['close'].values
            slope, _ = np.polyfit(x, y, 1)
            if abs(slope) > max_slope:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_REGRESSION_SLOPE. "
                                f"Got {abs(slope):.4f}, max {max_slope}.")
                return None

            max_balance_deviation = self.settings.max_time_balance_deviation_ratio
            candles_above = (consolidation_window['close'] > center_price).sum()
            candles_below = (consolidation_window['close'] < center_price).sum()
            balance_ratio = abs(candles_above - candles_below) / lookback
            if balance_ratio > max_balance_deviation:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MAX_TIME_BALANCE_DEVIATION_RATIO. "
                                f"Got {balance_ratio:.2f}, max {max_balance_deviation}.")
                return None

        if self.settings.use_consecutive_trend_check:
            max_consecutive = self.settings.max_consecutive_trend_candles
            
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

        min_peaks_troughs = self.settings.min_peaks_troughs
        if min_peaks_troughs > 0:
            prominence = self.settings.peak_trough_prominence
            peak_indices, _ = find_peaks(consolidation_window['high'], prominence=prominence)
            trough_indices, _ = find_peaks(-consolidation_window['low'], prominence=prominence)

            valid_peaks = [p for p in peak_indices if consolidation_window['high'].iloc[p] > center_price]
            valid_troughs = [t for t in trough_indices if consolidation_window['low'].iloc[t] < center_price]
            
            if len(valid_peaks) + len(valid_troughs) < min_peaks_troughs:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed MIN_PEAKS_TROUGHS. "
                                f"Got {len(valid_peaks) + len(valid_troughs)}, min {min_peaks_troughs}.")
                return None

            if self.settings.use_alternating_peaks_troughs_check:
                points = [(i, 'peak') for i in valid_peaks] + [(i, 'trough') for i in valid_troughs]
                points.sort(key=lambda x: x[0])

                if len(points) > 1:
                    is_alternating = all(points[i][1] != points[i+1][1] for i in range(len(points) - 1))
                    if not is_alternating:
                        self.logger.debug(f"Window ending {window.index[-1]}: Failed USE_ALTERNATING_PEAKS_TROUGHS_CHECK.")
                        return None

        if self.settings.use_adx_filter:
            adx_threshold = self.settings.adx_threshold
            min_non_trending_ratio = self.settings.adx_confirmation_ratio
            
            is_non_trending = consolidation_window['adx'] < adx_threshold
            
            if is_non_trending.mean() < min_non_trending_ratio:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed ADX_CONFIRMATION_RATIO. "
                                f"Got {is_non_trending.mean():.2f}, min {min_non_trending_ratio}.")
                return None

        if self.settings.use_bb_width_filter:
            bb_width_threshold = self.settings.bb_width_threshold_percent / 100
            bb_width_percent = consolidation_window['bb_width'] / consolidation_window['bb_middle']
            is_squeezed = bb_width_percent < bb_width_threshold
            
            min_squeeze_ratio = self.settings.bb_squeeze_confirmation_ratio
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

        if self.settings.use_volume_spike_confirmation:
            avg_consolidation_volume = consolidation_window['volume'].mean()
            volume_multiplier = self.settings.volume_spike_multiplier
            is_volume_spike = consolidation_window['volume'] > avg_consolidation_volume * volume_multiplier
            
            min_volume_spike_ratio = self.settings.min_volume_spike_confirmation_ratio
            if is_volume_spike.mean() < min_volume_spike_ratio:
                self.logger.debug(f"Window ending {window.index[-1]}: Failed VOLUME_SPIKE_CONFIRMATION_RATIO. "
                                f"Got {is_volume_spike.mean():.2f}, min {min_volume_spike_ratio}.")
                return None

        alert_time = window.index[-1]
        start_time = consolidation_window.index[0]
        if isinstance(start_time, pd.Timestamp):
            start_time = start_time.isoformat()
        
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        alert = AlertData(
            symbol=self.symbol,
            approach=self.APPROACH_NAME,
            id=alert_id,
            signal=signal,
            alert_price=breakout_candle['close'],
            alert_time=alert_time,
            start_price=center_price,
            start_time=start_time,
            magnitude=abs(breakout_candle['close'] - center_price),
            details=json.dumps({
                "lookback": lookback,
                "support": support,
                "resistance": resistance,
                "center_price": center_price,
                "max_deviation": max_deviation,
                "is_clustered": is_clustered.tolist(),
                "breakout_candle": {**breakout_candle[['open', 'high', 'low', 'close', 'volume']].to_dict(), 'time': breakout_candle.name},
                "consolidation_window": consolidation_window.reset_index()[['time', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient='records'),
                "breakout_window": breakout_window.reset_index()[['time', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient='records'),
            }, default=str)
        )

        self.logger.info(f"Window ending {window.index[-1]}: {signal} breakout detected. "
                        f"Support: {support}, Resistance: {resistance}.")
        
        return alert
