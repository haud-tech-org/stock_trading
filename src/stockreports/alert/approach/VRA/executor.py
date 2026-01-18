import pandas as pd
from scipy.signal import find_peaks
import logging
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import VraSettings
from src.stockreports.alert.common.confirmation.reversal import validate_reversal_confirmation
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.alert.common.signal.market_trend_validation import validate_concurrent_trend
from src.stockreports.utils.log_factory import log

class VraExecutor(Executor):
    APPROACH_NAME = Approach.VRA
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = VraSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        try:
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol
            )
            
            alerts_data = self._find_vra_alerts(df, new_candle_count)
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol
            )

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
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {window_size}, have {len(df)}.",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol
            )
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
            self.current_window_end_time = window_df.iloc[-1]['time']
            self.current_window_start_time = window_df.iloc[0]['time']
            self.current_step = 1

            # --- Validation Order for Performance ---

            # Step 1: Volume Spike Analysis
            volume_anchor_idx = window_df['volume'].idxmax()
            
            # Define the search window for the minimum volume: from the start of the window
            # up to (but not including) the candle with the maximum volume.
            pre_spike_df = window_df.loc[:volume_anchor_idx - 1]
            
            # If there are no candles before the spike, we cannot proceed.
            if pre_spike_df.empty:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Volume spike is the first candle; no preceding window to analyze.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Find the minimum volume within this preceding period.
            min_vol_idx = pre_spike_df['volume'].idxmin()
            
            candle_v = window_df.loc[volume_anchor_idx]
            min_vol_in_window = pre_spike_df.loc[min_vol_idx]['volume']
            if not (candle_v['volume'] >= self.settings.volume_multiplier * min_vol_in_window):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Volume spike ({candle_v['volume']}) did not meet the multiplier ({self.settings.volume_multiplier}) over minimum volume ({min_vol_in_window}).",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # New Volume Consistency Validation
            if not self._validate_volume_consistency(
                pre_spike_df=pre_spike_df,
                spike_candle=window_df.loc[volume_anchor_idx]
            ):
                continue

            # Step 2: Reversal Confirmation Window
            self.current_step += 1
            confirmation_df = window_df.loc[volume_anchor_idx:].copy()
            if len(confirmation_df) < 2:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Not enough data for reversal confirmation after volume spike.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            first_candle = window_df.iloc[0]
            reversal_signal = Signal.SELL if candle_v['close'] > first_candle['close'] else Signal.BUY

            # Step 3: Reversal Confirmation Logic
            self.current_step += 1
            validation_result = validate_reversal_confirmation(
                confirmation_df=confirmation_df, 
                reversal_signal=reversal_signal, 
                min_alert_body_size=self.settings.min_alert_body_size, 
                max_distance_close_price=self.settings.max_distance_close_price
            )
            if validation_result is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Reversal confirmation failed for {reversal_signal} signal.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            alert_candle, anchor_candle = validation_result

            # Step 4: Market Trend Validation
            self.current_step += 1
            if self.settings.enable_market_trend_validation:
                if not validate_concurrent_trend(
                    expected_signal=reversal_signal,
                    alert_time=alert_candle['time'],
                    min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                    require_all=False
                ):
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=alert_candle['time'],
                        step=self.current_step,
                        message=f"Concurrent market trend validation failed for {reversal_signal} signal.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue
            
            # Step 5: Magnitude Validation
            self.current_step += 1
            if reversal_signal == Signal.SELL:
                min_close_in_window = window_df['close'].min()
                magnitude = abs(anchor_candle['close'] - min_close_in_window)
            else: # BUY
                max_close_in_window = window_df['close'].max()
                magnitude = abs(max_close_in_window - anchor_candle['close'])

            if magnitude < self.settings.min_trend_magnitude:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=alert_candle['time'],
                    step=self.current_step,
                    message=f"Trend magnitude ({magnitude:.2f}) was less than the minimum required ({self.settings.min_trend_magnitude}).",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            # Step 6: Cooldown Logic
            self.current_step += 1
            if is_in_cooldown(
                new_alert_time=alert_candle['time'],
                new_signal=reversal_signal,
                latest_alert=VraExecutor.LATEST_ALERT,
                cooldown_window=self.settings.cooldown_window
            ):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=alert_candle['time'],
                    step=self.current_step,
                    message=f"Alert for {reversal_signal} is in cooldown.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
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

    def _validate_volume_consistency(self, pre_spike_df: pd.DataFrame, spike_candle: pd.Series) -> bool:
        """
        Validates that the volume spike is significant compared to the candles immediately preceding it.
        """
        consistent_window_size = self.settings.consistent_volume_window
        
        # Use as many candles as are available if the pre_spike_df is smaller than the configured window
        window_to_check = min(len(pre_spike_df), consistent_window_size)

        if window_to_check == 0:
            # This case is already handled by the pre_spike_df.empty check, but as a safeguard:
            return True # Or False, depending on desired strictness. Let's be lenient.

        # Get the last N candles from the pre-spike dataframe
        adjacent_candles = pre_spike_df.tail(window_to_check)
        
        # Count how many of these adjacent candles satisfy the volume condition
        succeed_count = 0
        for _, adjacent_candle in adjacent_candles.iterrows():
            if spike_candle['volume'] >= self.settings.volume_multiplier * adjacent_candle['volume']:
                succeed_count += 1
        
        # Check if the ratio of successful candles meets the minimum requirement
        success_ratio = succeed_count / window_to_check
        if success_ratio < self.settings.consistent_volume_min_percentage:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=1,
                message=f"Volume consistency check failed. Ratio {success_ratio:.2f} < min {self.settings.consistent_volume_min_percentage}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return False
            
        return True
