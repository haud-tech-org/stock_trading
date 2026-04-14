import pandas as pd
import logging
import json
from typing import Optional, Tuple

from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel, Trend, CandleColumn
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from .settings import ConsistentVolumeAnchorSettings
from .analyzer import ConsistentVolumeAnchorAnalyzer
from .validator import ConsistentVolumeAnchorValidator
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import candle_utils, window_utils


class ConsistentVolumeAnchorExecutor(Executor):
    """
    Executor for the Consistent Volume Anchor (CVA) approach.
    Detects reversal signals by identifying anchor candles with consistent volume patterns,
    then confirming with alert candles showing volume spikes and strong body sizes.
    """
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str, approach: Approach, resolution: int):
        self.settings = ConsistentVolumeAnchorSettings(symbol)
        self.analyzer = ConsistentVolumeAnchorAnalyzer()
        self.validator = ConsistentVolumeAnchorValidator()
        super().__init__(symbol, approach, resolution, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        lookback_window_size = self.settings.lookback_window

        if len(df) < lookback_window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {lookback_window_size}, have {len(df)}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return self.alerts

        # Setup median volume for volume consistency filtering
        self.median_volume = self._setup_median_volume(df)

        # Validate median volume is positive
        if self.median_volume <= 0.0:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Median volume is not positive: {self.median_volume}. Cannot proceed with alert detection.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return self.alerts

        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=lookback_window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, lookback_window_size)
            if self.lookback_window_df is None or self.last_candle is None:
                continue

            # Step 1: Find anchor candle
            self.next_step()
            anchor_index = self._step_find_anchor_candle(self.lookback_window_df)
            if anchor_index is None:
                continue

            # Step 2: Extract consistent volume window
            self.next_step()
            window_result = self._step_extract_consistent_window(
                self.lookback_window_df, anchor_index
            )
            if window_result is None:
                continue
            consistent_window_df = window_result

            # Step 3: Validate volume consistency
            self.next_step()
            volume_stats = self._step_validate_volume_consistency(consistent_window_df)
            if volume_stats is None:
                continue
            consistent_volume_window, min_vol, max_vol = volume_stats

            # Step 4: Validate consistent window body sizes
            self.next_step()
            body_size_result = self._step_validate_consistent_window_body_sizes(consistent_volume_window)
            if body_size_result is None:
                continue
            validated_window_size = body_size_result

            # Step 5: Validate alert candle volume
            self.next_step()
            if not self._step_validate_alert_candle_volume(self.last_candle, min_vol, max_vol):
                continue

            # Step 6: Validate alert candle body size
            self.next_step()
            if not self._step_validate_alert_candle_body(self.last_candle):
                continue

            # Step 7: Validate alert candle has largest body and meets body ratio threshold
            self.next_step()
            if not self._step_validate_alert_candle_largest_body_with_ratio(self.last_candle, self.lookback_window_df):
                continue

            # Step 8: Determine signal and trend
            self.next_step()
            signal_trend_result = self._step_determine_signal_and_trend(self.last_candle)
            if signal_trend_result is None:
                continue
            signal, trend = signal_trend_result

            # Step 9: Validate alert candle open price relative to consistent volume window
            self.next_step()
            if not self._step_validate_alert_candle_close_price(self.last_candle, signal, consistent_volume_window):
                continue

            # Step 10: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=ConsistentVolumeAnchorExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Alert creation
            self.next_step()
            details_alert_dict = self._add_details_for_alert(
                window_trend=consistent_volume_window,
                window_size=validated_window_size,
                min_vol_candle=consistent_volume_window.iloc[0],
                max_vol_candle=consistent_volume_window.iloc[-1]
            )

            alert_data = self._create_alert_with_details(
                final_signal=signal,
                final_trend=trend,
                final_alert_candle=self.last_candle,
                final_magnitude=self.settings.min_alert_magnitude,
                details=details_alert_dict
            )

            if alert_data is not None:
                self.alerts.append(alert_data)
                ConsistentVolumeAnchorExecutor.LATEST_ALERT = alert_data
            else:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    step=self.current_step,
                    message="Alert creation returned None. Alert not appended.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )

            if not self.is_development_mode and len(self.alerts) >= 1:
                return self.alerts

        return self.alerts[::-1]

    # --- PRIVATE HELPER METHODS (CVA-SPECIFIC) ---

    def _find_anchor_candle(self, lookback_window_df: pd.DataFrame) -> Optional[int]:
        """
        Find the first candle where volumes from start to this candle are always decreasing.
        Returns the index position in the DataFrame or None if not found.
        """
        volumes = lookback_window_df[CandleColumn.VOLUME].values
        
        for i in range(1, len(volumes)):
            # Check if volumes from 0 to i are strictly decreasing
            is_decreasing = all(volumes[j] > volumes[j+1] for j in range(i))
            if is_decreasing:
                return i
        
        return None

    def _extract_consistent_volume_window(
        self, lookback_window_df: pd.DataFrame, anchor_index: int
    ) -> Optional[pd.DataFrame]:
        """
        Extract window from anchor candle to the penultimate candle (excluding last candle).
        Returns: consistent_window_df or None if anchor is too close to the end
        """
        self.next_validation()
        
        # Window from anchor_index to len(df) - 2 (excluding last candle)
        end_index = len(lookback_window_df) - 1
        
        if anchor_index >= end_index:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Anchor candle too close to the end. Anchor index: {anchor_index}, End index: {end_index}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        consistent_window = lookback_window_df.iloc[anchor_index:end_index]

        return consistent_window

    def _step_find_anchor_candle(self, lookback_window_df: pd.DataFrame) -> Optional[int]:
        """
        Step 1: Find anchor candle (first candle with volume < any previous candles).
        """
        self.next_validation()
        
        anchor_index = self._find_anchor_candle(lookback_window_df)
        
        if anchor_index is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="No anchor candle found in the window.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        return anchor_index

    def _step_extract_consistent_window(
        self, lookback_window_df: pd.DataFrame, anchor_index: int
    ) -> Optional[pd.DataFrame]:
        """
        Step 2: Extract consistent volume window from anchor to penultimate candle.
        Returns: consistent_window_df or None if extraction fails
        """
        return self._extract_consistent_volume_window(lookback_window_df, anchor_index)

    def _step_validate_volume_consistency(
        self, consistent_window_df: pd.DataFrame
    ) -> Optional[Tuple[pd.DataFrame, float, float]]:
        """
        Step 3: Validate volume consistency and filter by body size in the window.
        - Filter candles that satisfy BOTH conditions:
          1. Volume <= median_volume (calculated from df starting at 09:30:00)
          2. Body size <= MAX_CONSISTENT_BODY_SIZE_CANDLE
        - Find min and max volume in the filtered consistent volume window
        - Returns: (consistent_volume_window_df, min_vol, max_vol) where consistent_volume_window_df
          contains only candles satisfying BOTH volume and body size conditions
        """
        self.next_validation()
        
        result = self.validator.validate_volume_and_body_consistency(
            consistent_window_df,
            self.median_volume,
            self.settings.max_consistent_volume_multiplier,
            self.settings.max_consistent_body_size_candle,
            self.settings.consistent_candle_percentage
        )
        
        if result is None:
            filtered_count = len(
                ConsistentVolumeAnchorAnalyzer.filter_window_by_volume_and_body(
                    consistent_window_df,
                    self.median_volume,
                    self.settings.max_consistent_volume_multiplier,
                    self.settings.max_consistent_body_size_candle
                )
            )
            percentage = (
                filtered_count / len(consistent_window_df)
                if len(consistent_window_df) > 0 else 0
            )
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Consistent candles percentage below threshold. Percentage: {percentage:.2%}, Required: {self.settings.consistent_candle_percentage:.2%}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None
        
        consistent_volume_window, min_vol, max_vol = result
        
        self.validations.append(Validation(
            name=nameof(self.settings.consistent_candle_percentage),
            step=self.current_step,
            validation=self.validation_step,
            message="Consistent candles meet percentage (volume <= median and body size <= threshold).",
            status=ValidationStatus.PASSED
        ))

        return consistent_volume_window, min_vol, max_vol

    def _step_validate_consistent_window_body_sizes(
        self, consistent_window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Step 4: Validate consistent window size (price range).
        - Calculate the price range (max - min) of the consistent volume window
        - Ensure window size <= MAX_CONSISTENT_WINDOW_SIZE threshold
        - NOTE: Body size filtering now consolidated in Step 3 (volume consistency step)
        - Returns: window_size (price range) if valid, None otherwise
        """
        self.next_validation()
        
        is_valid = self.validator.validate_window_price_range(
            consistent_window_df,
            self.settings.max_consistent_window_size
        )
        
        if not is_valid:
            window_size = (
                ConsistentVolumeAnchorAnalyzer.calculate_window_price_range(
                    consistent_window_df
                )
            )
            if window_size is not None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Window size exceeds threshold. Size: {window_size:.2f}, Max: {self.settings.max_consistent_window_size}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            return None

        window_size = (
            ConsistentVolumeAnchorAnalyzer.calculate_window_price_range(
                consistent_window_df
            )
        )
        
        self.validations.append(Validation(
            name=nameof(self.settings.max_consistent_window_size),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Window size within limits. Size: {window_size:.2f}" if window_size else "Window size within limits.",
            status=ValidationStatus.PASSED
        ))

        return window_size

    def _step_validate_alert_candle_volume(
        self, alert_candle: pd.Series, min_vol: float, max_vol: float
    ) -> bool:
        """
        Step 5: Validate alert candle (last candle) volume.
        - Alert volume >= max volume in consistent window
        - Alert volume >= MIN_VOLUME_CONFIRMATION_MULTIPLIER * min volume in consistent window
        """
        self.next_validation()
        
        is_valid = self.validator.validate_alert_volume(
            alert_candle,
            max_vol,
            min_vol,
            self.settings.min_volume_confirmation_multiplier
        )
        
        if not is_valid:
            alert_vol = alert_candle[CandleColumn.VOLUME]
            if alert_vol < max_vol:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Alert candle volume less than max window volume. Alert: {alert_vol:.2f}, Max: {max_vol:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            else:
                threshold_vol = (
                    self.settings.min_volume_confirmation_multiplier *
                    min_vol
                )
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Alert candle volume below confirmation threshold. Alert: {alert_vol:.2f}, Threshold: {threshold_vol:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            return False

        self.validations.append(Validation(
            name=nameof(self.settings.min_volume_confirmation_multiplier),
            step=self.current_step,
            validation=self.validation_step,
            message="Alert candle volume confirmed.",
            status=ValidationStatus.PASSED
        ))

        return True

    def _step_validate_alert_candle_body(self, alert_candle: pd.Series) -> bool:
        """
        Step 6: Validate alert candle body size.
        """
        self.next_validation()
        
        is_valid = self.validator.validate_alert_body_size(
            alert_candle,
            self.settings.min_body_size_alert_candle
        )
        
        if not is_valid:
            body_size = abs(
                alert_candle[CandleColumn.CLOSE] - alert_candle[CandleColumn.OPEN]
            )
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Alert candle body size below minimum. Body: {body_size:.2f}, Min: {self.settings.min_body_size_alert_candle}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False

        self.validations.append(Validation(
            name=nameof(self.settings.min_body_size_alert_candle),
            step=self.current_step,
            validation=self.validation_step,
            message="Alert candle body size meets minimum.",
            status=ValidationStatus.PASSED
        ))

        return True

    def _step_validate_alert_candle_largest_body_with_ratio(
        self, alert_candle: pd.Series, lookback_window_df: pd.DataFrame
    ) -> bool:
        """
        Step 7: Validate alert candle has the largest body in the lookback window
        and its body ratio (body / range) >= MIN_BODY_RATIO.
        - Calculate body size for all candles in lookback window
        - Ensure alert candle has the largest body
        - Ensure body ratio (body / (high - low)) >= MIN_BODY_RATIO threshold
        """
        self.next_validation()
        
        is_valid = self.validator.validate_alert_largest_body_with_ratio(
            alert_candle,
            lookback_window_df,
            self.settings.min_body_ratio
        )
        
        if not is_valid:
            alert_body = abs(
                alert_candle[CandleColumn.CLOSE] - alert_candle[CandleColumn.OPEN]
            )
            max_body = (
                ConsistentVolumeAnchorAnalyzer.get_max_body_in_window(
                    lookback_window_df
                )
            )
            
            if alert_body < max_body:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Alert candle does not have the largest body. Alert body: {alert_body:.2f}, Max body: {max_body:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            else:
                body_ratio = (
                    ConsistentVolumeAnchorAnalyzer.calculate_alert_body_ratio(
                        alert_candle
                    ) or 0
                )
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Alert candle body ratio below minimum. Ratio: {body_ratio:.2%}, Min: {self.settings.min_body_ratio:.2%}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            return False

        self.validations.append(Validation(
            name=nameof(self.settings.min_body_ratio),
            step=self.current_step,
            validation=self.validation_step,
            message="Alert candle has largest body with sufficient ratio.",
            status=ValidationStatus.PASSED
        ))

        return True

    def _step_determine_signal_and_trend(self, alert_candle: pd.Series) -> Optional[Tuple[Signal, Trend]]:
        """
        Step 7: Determine signal and trend based on alert candle color.
        - Green candle (close > open) → Signal.BUY, Trend.UPTREND
        - Red candle (close < open) → Signal.SELL, Trend.DOWNTREND
        """
        trend = candle_utils.get_trend_from_candle(alert_candle)
        
        if trend is None or trend == Trend.NEUTRAL:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Unable to determine trend from alert candle.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        signal = candle_utils.get_signal_from_trend(trend)

        return signal, trend

    def _step_validate_alert_candle_close_price(
        self, alert_candle: pd.Series, signal: Signal, consistent_volume_window: pd.DataFrame
    ) -> bool:
        """
        Step 8: Validate alert candle close price relative to consistent volume window.
        - If BUY signal: close price must be higher than max(open, close) of consistent volume window
        - If SELL signal: close price must be lower than min(open, close) of consistent volume window
        """
        self.next_validation()
        
        is_valid = self.validator.validate_alert_price_direction(
            alert_candle,
            signal,
            consistent_volume_window
        )
        
        if not is_valid:
            alert_close = alert_candle[CandleColumn.CLOSE]
            window_opens = consistent_volume_window[CandleColumn.OPEN]
            window_closes = consistent_volume_window[CandleColumn.CLOSE]
            prices = pd.concat([window_opens, window_closes])
            
            if signal == Signal.BUY:
                max_price = prices.max()
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"BUY signal: Alert close price not above window max. Alert close: {alert_close:.2f}, Window max: {max_price:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            else:  # SELL
                min_price = prices.min()
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"SELL signal: Alert close price not below window min. Alert close: {alert_close:.2f}, Window min: {min_price:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
            return False

        self.validations.append(Validation(
            name="alert_price_direction",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Alert candle price in correct direction for {signal} signal.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _setup_median_volume(self, df: pd.DataFrame) -> float:
        """
        Calculate and return the median volume for the entire DataFrame.
        - Filters data from market open (09:30:00) to end of day using window_utils
        - Calculates median volume from filtered data using window_utils
        - Falls back to overall DataFrame median if filtered data is empty
        - This value is used in Step 3 for consistent volume window filtering
        
        Returns:
            The median volume (float). Returns 0.0 if no valid volume data found.
        """
        # Filter data from 09:30:00 onwards using utility function
        df_filtered = window_utils.filter_data_by_time_range(df, start_time='09:30:00')
        
        # Calculate median volume using utility function, with fallback
        return window_utils.get_median_volume(df_filtered)
