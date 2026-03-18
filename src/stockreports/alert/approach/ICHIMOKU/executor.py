# src/stockreports/alert/approach/ICHIMOKU/executor.py
import pandas as pd
from typing import List
import logging

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertData, Validation
from src.stockreports.alert.common.constants import Approach, Signal, Trend
from src.stockreports.utils.log_factory import log, LogLevel, ValidationStatus

from .settings import IchimokuSettings
from .analyzer import IchimokuAnalyzer
from .validator import IchimokuValidator


class IchimokuExecutor(Executor):
    """
    Ichimoku Cloud signal detector.
    
    Implements the Ichimoku Kinko Hyo technical analysis approach.
    Detects BUY/SELL signals based on:
    1. Tenkan-sen (9) crossing Kijun-sen (26) - momentum shift
    2. Price position relative to Cloud (Senkou A/B) - trend validation
    3. Chikou span (26-period lag) confirmation - strength confirmation
    """
    
    def __init__(self, symbol: str):
        """
        Initialize Ichimoku executor.
        
        Args:
            symbol (str): Trading symbol (e.g., 'VN30F1M', 'AAPL')
        """
        self.settings = IchimokuSettings(symbol)
        approach_name = Approach.ICHIMOKU
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)
    
    def _build_alert_from_signal(self, candle: pd.Series, signal: Signal) -> AlertData:
        """
        Build an alert from detected signal.
        
        Args:
            candle (pd.Series): Current candle with OHLCV and Ichimoku indicators
            signal (Signal): Detected signal (BUY or SELL)
            
        Returns:
            AlertData: Alert instance or None if creation fails
        """
        try:
            # Determine trend based on signal
            trend = Trend.UPTREND if signal == Signal.BUY else Trend.DOWNTREND
            
            # Build alert details with Ichimoku component values
            details = {
                "tenkan_sen": round(float(candle.get('tenkan_sen', 0)), 2),
                "kijun_sen": round(float(candle.get('kijun_sen', 0)), 2),
                "senkou_a": round(float(candle.get('senkou_a', 0)), 2),
                "senkou_b": round(float(candle.get('senkou_b', 0)), 2),
                "chikou_span": round(float(candle.get('chikou_span', 0)), 2),
            }
            
            # Use base class method to create alert with details
            # Get the maximum of configured threshold or calculated magnitude
            calculated_magnitude = abs(float(candle['close']) - float(self.first_candle['open']))
            final_magnitude = max(self.settings.magnitude_threshold, calculated_magnitude)
            
            alert = self._create_alert_with_details(
                final_signal=signal,
                final_trend=trend,
                details=details,
                final_alert_candle=candle,
                final_magnitude=final_magnitude
            )
            
            return alert
        except Exception as e:
            self.logger.error(f"Error creating alert: {str(e)}")
            return None
    
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> List[AlertData]:
        """
        Implement abstract method from base Executor.
        Finds all Ichimoku signals in the provided dataframe.
        
        Args:
            df (pd.DataFrame): OHLCV data with columns: 'time', 'open', 'high', 'low', 'close', 'volume'
            new_candle_count (int): Number of new candles to process (0 = all)
            
        Returns:
            List[AlertData]: List of detected Ichimoku alerts
        """
        alerts = []
        
        try:
            # --- Pre-loop setup and validation ---
            # Validate data sufficiency (approach-specific)
            is_valid, validation_reason = IchimokuValidator.validate_data_sufficiency(
                df, self.settings
            )
            if not is_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    step=0,
                    message=f"Data validation failed: {validation_reason}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=Approach.ICHIMOKU
                )
                return alerts
            
            # Calculate all Ichimoku components
            df_with_indicators = IchimokuAnalyzer.calculate_all_components(
                df, self.settings
            )
            if df_with_indicators is None or df_with_indicators.empty:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    step=0,
                    message="Failed to calculate Ichimoku components",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=Approach.ICHIMOKU
                )
                return alerts
            
            # Validate all Ichimoku components exist and have no NaN values
            is_valid, validation_reason = IchimokuValidator.validate_components(
                df_with_indicators, self.settings
            )
            if not is_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    step=0,
                    message=f"Component validation failed: {validation_reason}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=Approach.ICHIMOKU
                )
                return alerts
            
            # Setup loop boundaries using base class method
            lookback_window_size = self.settings.lookback_window_size
            df_indexed, loop_start, loop_end = self.get_loop_setup(
                df_with_indicators, new_candle_count, lookback_window_size
            )
            
            # Limit loop_end to avoid NaN values from senkou shift at the tail
            # senkou_a/senkou_b have NaN in the last senkou_shift_period rows (forward shift)
            # When new_candles are added beyond the usable range, adjust loop boundaries
            # to scan the requested new_candle_count within the valid range
            shift_offset = self.settings.senkou_shift_period
            max_usable_idx = len(df_indexed) - shift_offset
            original_loop_end = loop_end
            loop_end = min(loop_end, max_usable_idx)
            
            # If loop_end was constrained and we're in production mode (new_candle_count < total),
            # adjust loop_start to scan new_candle_count candles from the end of usable range
            if loop_end < original_loop_end and not self.is_development_mode:
                # Scan the last new_candle_count candles within the usable range
                # Range goes backwards, so start from (end-1) and go back new_candle_count positions
                adjusted_loop_start = max(lookback_window_size, loop_end - new_candle_count)
                loop_start = adjusted_loop_start
            
            # DEBUG: Log loop setup parameters
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                step=0,
                message=f"Loop setup: total_len={len(df_indexed)}, loop_start={loop_start}, loop_end={loop_end}, max_usable_idx={max_usable_idx}, lookback_size={lookback_window_size}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=Approach.ICHIMOKU
            )
            
            # --- Main processing loop ---
            for i in range(loop_end - 1, loop_start - 1, -1):
                # Extract window context using base class method
                self.set_window_context(i, df_indexed, lookback_window_size)
                if self.lookback_window_df is None or self.last_candle is None:
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        step=1,
                        message=f"Window context extraction failed at index {i}",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        approach=Approach.ICHIMOKU
                    )
                    continue
                
                # Update window end time to the forward-shifted candle (for Senkou indicator alignment)
                # and get the shifted candle for later use in alert creation
                success, shifted_candle = self.update_window_end_time_with_shift(i, df_indexed, shift_offset)
                if not success or shifted_candle is None:
                    # Shifted index out of bounds or failed, skip this signal
                    continue
                
                # Get the current candle at index i for signal detection and validation
                current_candle_full = df_indexed.iloc[i]
                
                # DEBUG: Log which index we're processing
                candle_time = current_candle_full.get('time') if current_candle_full is not None else 'N/A'
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    step=1,
                    message=f"Processing index {i}, candle_time={candle_time}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=Approach.ICHIMOKU
                )
                
                # Step 1: Detect signal (Tenkan crossing Kijun)
                # Need to check current candle (at i) vs previous (at i-1)
                # Build a small window with just current and previous
                if i < 1:
                    continue
                signal_window = df_indexed.iloc[i-1:i+1]  # Get [i-1, i]
                self.next_step()
                signal = self._step_detect_tenkan_kijun_signal(signal_window)
                if signal is None:
                    continue
                
                # Step 2: Validate trend (price vs cloud) - use current candle
                self.next_step()
                if not self._step_validate_price_cloud_position_current(current_candle_full, signal):
                    continue
                
                # Step 3: Validate Chikou confirmation (conditional)
                if not self.settings.skip_chikou_confirmation:
                    self.next_step()
                    # Chikou needs historical context, use full window plus current
                    chikou_window = df_indexed.iloc[i-lookback_window_size:i+1]
                    window_current_idx = len(chikou_window) - 1
                    if not self._step_validate_chikou_confirmation(chikou_window, window_current_idx, signal):
                        continue
                
                # Step 4: Create alert - use shifted candle (aligned with Senkou indicators)
                self.next_step()
                alert = self._step_create_alert(shifted_candle, signal)
                if alert is None:
                    continue
                
                # Step 5: Add to results with success log
                self.next_step()
                alerts.append(alert)
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    step=self.current_step,
                    message=f"Ichimoku {signal} alert detected",
                    log_level=LogLevel.INFO,
                    execution_symbol=self.symbol,
                    alert_time=self.current_window_end_time,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=Approach.ICHIMOKU
                )
                
                # Return immediately after finding first alert (deployment behavior)
                if alerts:
                    return alerts
            
            # Return alerts in chronological order
            return alerts[::-1] if alerts else alerts
            
        except Exception as e:
            self.logger.error(
                f"Exception in {Approach.ICHIMOKU}._find_alerts(): {str(e)}"
            )
            return alerts
    
    def _step_detect_tenkan_kijun_signal(self, lookback_window_df: pd.DataFrame) -> Signal:
        """
        Step 1: Detect Tenkan-Kijun crossover signal.
        
        Returns:
            Signal: BUY or SELL signal if crossover detected, None otherwise
        """
        self.next_validation()
        window_current_idx = len(lookback_window_df) - 1
        signal = IchimokuValidator.detect_signal(lookback_window_df, window_current_idx)
        
        if signal is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                step=self.current_step,
                validation=self.validation_step,
                message="Tenkan-Kijun crossover not detected",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                alert_time=self.current_window_end_time,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=Approach.ICHIMOKU
            )
            return None
        
        self.validations.append(Validation(
            name="Tenkan-Kijun Crossover",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Tenkan-Kijun {signal} crossover detected",
            status=ValidationStatus.PASSED
        ))
        
        return signal
    
    def _step_validate_price_cloud_position_current(self, candle: pd.Series, signal: Signal) -> bool:
        """
        Step 2: Validate price position relative to Ichimoku Cloud (single candle version).
        
        Args:
            candle (pd.Series): Current candle to validate
            signal (Signal): Detected signal
            
        Returns:
            bool: True if price position confirms signal, False otherwise
        """
        self.next_validation()
        is_valid = IchimokuValidator.validate_trend(candle, signal)
        
        if not is_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Price-Cloud validation failed for {signal}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                alert_time=self.current_window_end_time,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=Approach.ICHIMOKU
            )
            return False
        
        self.validations.append(Validation(
            name="Price-Cloud Position",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Price correctly positioned vs Cloud for {signal}",
            status=ValidationStatus.PASSED
        ))
        
        return True
    
    def _step_validate_price_cloud_position(self, lookback_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 2: Validate price position relative to Ichimoku Cloud.
        
        Returns:
            bool: True if price position confirms signal, False otherwise
        """
        self.next_validation()
        window_current_idx = len(lookback_window_df) - 1
        is_valid = IchimokuValidator.validate_trend(
            lookback_window_df.iloc[window_current_idx], signal
        )
        
        if not is_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Price-Cloud validation failed for {signal}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                alert_time=self.current_window_end_time,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=Approach.ICHIMOKU
            )
            return False
        
        self.validations.append(Validation(
            name="Price-Cloud Position",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Price correctly positioned vs Cloud for {signal}",
            status=ValidationStatus.PASSED
        ))
        
        return True
    
    def _step_validate_chikou_confirmation(self, lookback_window_df: pd.DataFrame, window_current_idx: int, signal: Signal) -> bool:
        """
        Step 3: Validate Chikou span confirmation.
        
        Returns:
            bool: True if Chikou confirms signal, False otherwise
        """
        self.next_validation()
        is_valid = IchimokuValidator.validate_chikou(
            lookback_window_df, window_current_idx, signal, self.settings
        )
        
        if not is_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Chikou confirmation failed for {signal}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                alert_time=self.current_window_end_time,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=Approach.ICHIMOKU
            )
            return False
        
        self.validations.append(Validation(
            name="Chikou Confirmation",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Chikou span confirms {signal} signal",
            status=ValidationStatus.PASSED
        ))
        
        return True
    
    def _step_create_alert(self, candle: pd.Series, signal: Signal) -> AlertData:
        """
        Step 4: Create alert object from validated signal.
        
        Returns:
            AlertData: Alert object if creation succeeds, None otherwise
        """
        self.next_validation()
        alert = self._build_alert_from_signal(candle, signal)
        
        if alert is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                step=self.current_step,
                validation=self.validation_step,
                message="Alert creation failed",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                alert_time=self.current_window_end_time,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=Approach.ICHIMOKU
            )
            return None
        
        self.validations.append(Validation(
            name="Alert Creation",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Alert object created for {signal}",
            status=ValidationStatus.PASSED
        ))
        
        return alert