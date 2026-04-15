"""Main executor for REVERSAL_ANCHOR_SIGNAL_CANDLE approach."""

from typing import Optional, Tuple
import pandas as pd
import logging
from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import (
    Approach,
    Signal,
    Trend,
    ValidationStatus,
    LogLevel,
)
from src.stockreports.alert.model.models import AlertData, Validation
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import candle_utils
from .settings import ReversalAnchorSignalCandleSettings
from .analyzer import ReversalAnchorSignalCandleAnalyzer
from .validator import ReversalAnchorSignalCandleValidator


class ReversalAnchorSignalCandleExecutor(Executor):
    """Executor for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.
    
    Detects potential trend reversals by analyzing:
    1. Anchor candle (largest body in lookback window)
    2. Signal candle (highest volume at or after anchor)
    3. Alert candle (final candle with extreme values and wick characteristics)
    
    Signal Generation:
    - SELL alert: When uptrend reversal is detected
    - BUY alert: When downtrend reversal is detected
    """

    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str, approach: Approach, resolution: int) -> None:
        """Initialize REVERSAL_ANCHOR_SIGNAL_CANDLE executor.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
            approach: Approach constant (Approach.REVERSAL_ANCHOR_SIGNAL_CANDLE)
            resolution: Data resolution in minutes
        """
        self.settings = ReversalAnchorSignalCandleSettings(symbol)
        self.analyzer = ReversalAnchorSignalCandleAnalyzer()
        self.validator = ReversalAnchorSignalCandleValidator()
        super().__init__(symbol, approach, resolution, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(
        self,
        df: pd.DataFrame,
        new_candle_count: int = 0,
    ) -> list[AlertData]:
        """Find all reversal anchor signal candle alerts in price data.
        
        Main entry point for alert detection. Scans through data looking for
        reversal patterns and generates alerts when all validations pass.
        
        Args:
            df: OHLCV DataFrame (must have index as timestamps)
            new_candle_count: Number of new candles since last run (optional)
            
        Returns:
            List of AlertData objects representing detected reversals
        """
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

        # --- Standardized loop setup ---
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=lookback_window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            # --- Standardized window context extraction ---
            self.set_window_context(i, df_indexed, lookback_window_size)
            if self.lookback_window_df is None or self.last_candle is None:
                continue

            # Step 1: Analyze window trend and size
            self.next_step()
            trend_result = self._step_analyze_window_trend()
            if trend_result is None:
                continue
            trend, window_size = trend_result

            # Step 2: Validate anchor candle
            self.next_step()
            anchor_result = self._step_validate_anchor_candle()
            if anchor_result is None:
                continue
            anchor_idx, anchor_body = anchor_result

            # Step 3: Validate signal candle
            self.next_step()
            signal_result = self._step_validate_signal_candle(anchor_idx)
            if signal_result is None:
                continue
            signal_idx, signal_volume = signal_result

            # Step 4: Validate alert candle (doji, extremes, wick)
            self.next_step()
            wick_pct = self._step_validate_alert_candle(trend)
            if wick_pct is None:
                continue

            # Determine reversal trend and signal
            # If original trend is UPTREND, reversal is DOWNTREND (bearish) → SELL
            # If original trend is DOWNTREND, reversal is UPTREND (bullish) → BUY
            reversal_trend = Trend.DOWNTREND if trend == Trend.UPTREND else Trend.UPTREND
            reversal_signal = candle_utils.get_signal_from_trend(reversal_trend)

            # Step 5: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=ReversalAnchorSignalCandleExecutor.LATEST_ALERT,
                signal=reversal_signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue
            
            # Step 6: Alert creation
            self.next_step()
            details_dict = self._add_details_for_alert(
                window_size=window_size,
                anchor_body=anchor_body,
                signal_volume=signal_volume,
                wick_percentage=wick_pct,
            )

            alert_data = self._create_alert_with_details(
                final_signal=reversal_signal,
                final_trend=reversal_trend,
                final_alert_candle=self.last_candle,
                final_magnitude=window_size,
                details=details_dict
            )

            if alert_data is not None:
                self.alerts.append(alert_data)
                ReversalAnchorSignalCandleExecutor.LATEST_ALERT = alert_data

                if not self.is_development_mode:
                    return self.alerts

        return self.alerts

    def _step_analyze_window_trend(self) -> Optional[Tuple[Trend, float]]:
        """Step 1: Analyze window trend and size.
        
        Determines the trend direction and window price range using analyzer.
        
        Returns:
            Tuple of (trend, window_size) if successful, None otherwise
        """
        self.next_validation()
        try:
            trend, window_size = self.analyzer.analyze_window_trend(self.lookback_window_df)
            
            # Validate window size
            is_valid = self.validator.validate_window_size(
                window_size,
                self.settings.min_size_price_window,
            )
            
            if not is_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Window size {window_size:.2f} below minimum {self.settings.min_size_price_window}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            self.validations.append(Validation(
                name=nameof(self.settings.min_size_price_window),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window size validation passed",
                status=ValidationStatus.PASSED
            ))
            
            return trend, window_size
            
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window analysis failed - {str(e)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

    def _step_validate_anchor_candle(self) -> Optional[Tuple[pd.Timestamp, float]]:
        """Step 2: Find and validate anchor candle.
        
        Locates candle with largest body and validates it meets size requirements.
        
        Returns:
            Tuple of (anchor_timestamp, anchor_body) where anchor_timestamp is pd.Timestamp, None otherwise
        """
        self.next_validation()
        try:
            anchor_idx, anchor_body = self.analyzer.find_anchor_candle(self.lookback_window_df)
            average_body = self.analyzer.calculate_average_body_size(self.lookback_window_df)
            
            is_valid = self.validator.validate_anchor_candle(
                anchor_body,
                average_body,
                self.settings.min_size_candle,
                self.settings.multiplier_size,
            )
            
            if not is_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Anchor body {anchor_body:.2f} invalid (avg: {average_body:.2f})",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            self.validations.append(Validation(
                name=nameof(self.settings.min_size_candle),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Anchor candle validation passed",
                status=ValidationStatus.PASSED
            ))
            
            return anchor_idx, anchor_body
            
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Anchor candle validation failed - {str(e)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

    def _step_validate_signal_candle(self, anchor_idx: pd.Timestamp) -> Optional[Tuple[pd.Timestamp, float]]:
        """Step 3: Find and validate signal candle.
        
        Locates highest volume candle at or after anchor and validates it.
        
        Args:
            anchor_idx: pd.Timestamp of the anchor candle (must match DataFrame index type)
            
        Returns:
            Tuple of (signal_timestamp, signal_volume) where signal_timestamp is pd.Timestamp, None otherwise
        """
        self.next_validation()
        try:
            signal_idx, signal_volume = self.analyzer.find_signal_candle(
                self.lookback_window_df,
                anchor_idx,
            )
            average_volume = self.analyzer.calculate_average_volume(self.lookback_window_df)
            
            is_valid = self.validator.validate_signal_candle(
                signal_volume,
                average_volume,
                self.settings.min_volume,
                self.settings.multiplier_volume,
            )
            
            if not is_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Signal volume {signal_volume:.0f} invalid (avg: {average_volume:.0f})",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            self.validations.append(Validation(
                name=nameof(self.settings.min_volume),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Signal candle validation passed",
                status=ValidationStatus.PASSED
            ))
            
            return signal_idx, signal_volume
            
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Signal candle validation failed - {str(e)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

    def _step_validate_alert_candle(self, trend: Trend) -> Optional[float]:
        """Step 4: Validate alert candle (doji, extremes, wick).
        
        Checks if alert candle is not doji, has extremes, and wick within range.
        
        Args:
            trend: The identified trend (UPTREND or DOWNTREND)
            
        Returns:
            Wick percentage if valid, None otherwise
        """
        # Check 4a: Not a doji
        self.next_validation()
        try:
            is_doji = self.validator.validate_alert_candle_is_doji(self.last_candle)
            if is_doji:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Alert candle is doji (fails validation)",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            self.validations.append(Validation(
                name="alert_candle_not_doji",
                step=self.current_step,
                validation=self.validation_step,
                message="Alert candle is not doji",
                status=ValidationStatus.PASSED
            ))
            
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Doji check failed - {str(e)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

        # Check 4b: Alert has extremes
        self.next_validation()
        try:
            is_extreme = self.validator.validate_alert_candle_extremes(
                self.last_candle,
                trend,
                self.lookback_window_df,
            )
            
            if not is_extreme:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Alert candle not extreme for {trend}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            self.validations.append(Validation(
                name="alert_candle_extreme",
                step=self.current_step,
                validation=self.validation_step,
                message=f"Alert candle has extremes for {trend}",
                status=ValidationStatus.PASSED
            ))
            
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Extremes check failed - {str(e)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

        # Check 4c: Wick percentage within range
        self.next_validation()
        try:
            wick_pct = self.analyzer.calculate_wick_percentage(self.last_candle, trend)
            
            is_valid = self.validator.validate_alert_candle_wick(
                wick_pct,
                self.settings.min_percentage,
                self.settings.max_percentage,
            )
            
            if not is_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Wick {wick_pct:.2%} outside range [{self.settings.min_percentage:.2%}, {self.settings.max_percentage:.2%}]",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            self.validations.append(Validation(
                name=nameof(self.settings.min_percentage),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Wick percentage validation passed",
                status=ValidationStatus.PASSED
            ))
            
            return wick_pct
            
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Wick percentage check failed - {str(e)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None


