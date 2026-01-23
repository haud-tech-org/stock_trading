import pandas as pd
import logging
import json
from typing import Optional

from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.model.models import Validation
from .settings import VraSettings
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import window_utils, candle_utils

class VraExecutor(Executor):
    APPROACH_NAME = Approach.VRA
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = VraSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

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

        df_indexed, loop_start, loop_end = self.get_loop_setup(
            is_development_mode,
            df,
            new_candle_count,
            window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            (
                window_df,
                first_candle,
                alert_candle,
                self.current_window_start_time,
                self.current_window_end_time,
                self.current_step
            ) = self.get_window_context(
                i,
                df_indexed,
                window_size
            )
            if window_df is None or first_candle is None or alert_candle is None:
                continue

            # Step 1: Volume Validation
            self.next_step()
            vol_result = self._step_volume_validation(window_df, alert_candle)
            if vol_result is None:
                continue
            max_vol_candle, min_vol_candle = vol_result

            # Step 2: Trend & Magnitude Validation
            self.next_step()
            trend_result = self._step_trend_and_magnitude_validation(window_df, min_vol_candle, max_vol_candle)
            if trend_result is None:
                continue
            window_trend, window_size_val = trend_result

            reversal_signal = Signal.SELL if window_trend == Trend.UPTREND else Signal.BUY

            # Step 3: Cooldown Check
            self.next_step()
            if not self._step_cooldown_check(reversal_signal):
                continue

            # Step 4: Alert Creation
            self.next_step()
            alert_data = self._step_create_alert(
                first_candle,
                alert_candle,
                window_trend,
                window_size_val,
                max_vol_candle,
                min_vol_candle,
                reversal_signal
            )
            alerts.append(alert_data)
            VraExecutor.LATEST_ALERT = alert_data

        return alerts

    def _step_volume_validation(self, window_df, alert_candle) -> Optional[tuple[pd.Series, pd.Series]]:
        # Step 1: Find the max volume candle in the window
        self.next_validation()
        max_vol_candle = candle_utils.find_max_volume_candle(window_df)
        # Ensure the alert candle is the max volume candle
        if alert_candle.name != max_vol_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Alert candle is not the max volume candle in the lookback window.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Step 2: Find the min volume candle and check volume ratio
        self.next_validation()
        min_vol_candle = candle_utils.find_min_volume_candle(window_df)
        is_volume_ratio_valid, volume_ratio = candle_utils.validate_volume_ratio(max_vol_candle, min_vol_candle, self.settings.volume_multiplier)
        # Ensure the volume ratio between max and min meets the threshold
        if not is_volume_ratio_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Volume ratio is not significant enough. Ratio: {volume_ratio:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
        # Log a successful volume ratio validation
        self.validations.append(Validation(
            name=nameof(self.settings.volume_multiplier),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Volume ratio is significant. Ratio: {volume_ratio:.2f}",
            status=ValidationStatus.PASSED
        ))

        # Step 3: Ensure the min volume candle occurs before the max volume candle
        self.next_validation()
        if min_vol_candle.name >= max_vol_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Min volume candle did not occur before max volume candle.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # All validations passed; return the max and min volume candles
        return max_vol_candle, min_vol_candle

    def _step_trend_and_magnitude_validation(self, window_df, min_vol_candle: pd.Series, max_vol_candle: pd.Series) -> Optional[tuple[Trend, float]]:
        # Ensure min_vol_candle occurs before max_vol_candle
        if min_vol_candle.name >= max_vol_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Min volume candle did not occur before max volume candle.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Slice window_df from min_vol_candle to max_vol_candle (inclusive)
        try:
            start_idx = window_df.index.get_loc(min_vol_candle.name)
            end_idx = window_df.index.get_loc(max_vol_candle.name)
            if start_idx > end_idx:
                # Defensive: should not happen due to check above
                return None
            trend_window = window_df.iloc[start_idx:end_idx+1]
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Error slicing window_df for trend validation: {e}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Validate trend and magnitude on the sliced window
        window_trend, window_size_val = self._validate_trend_and_magnitude(trend_window)
        if window_trend is None or window_size_val is None:
            return None
        return window_trend, window_size_val

    def _step_cooldown_check(self, reversal_signal: Signal) -> bool:
        if is_in_cooldown(
            new_alert_time=self.current_window_end_time,
            new_signal=reversal_signal,
            latest_alert=VraExecutor.LATEST_ALERT,
            cooldown_window=self.settings.cooldown_window
        ):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Alert is in cooldown period.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return False
        self.validations.append(Validation(
            name=nameof(self.settings.cooldown_window),
            step=self.current_step,
            validation=self.validation_step,
            message="Alert is not in cooldown period.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_create_alert(
        self,
        first_candle: pd.Series,
        alert_candle: pd.Series,
        window_trend: Trend,
        window_size_val: float,
        max_vol_candle: pd.Series,
        min_vol_candle: pd.Series,
        reversal_signal: Signal
    ) -> AlertData:
        alert_id = str(int(self.current_window_end_time.timestamp()))
        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            approach=self.APPROACH_NAME,
            signal=reversal_signal,
            alert_price=alert_candle['close'],
            alert_time=self.current_window_end_time,
            start_price=first_candle['open'],
            start_time=self.current_window_start_time,
            magnitude=abs(window_size_val),
            details=json.dumps({
                "trend": window_trend,
                "max_volume_candle_time": str(max_vol_candle['time']),
                "min_volume_candle_time": str(min_vol_candle['time']),
                "validations": [v.to_json() for v in self.validations]
            })
        )

    def _validate_trend_and_magnitude(self, trend_window) -> Optional[tuple[Trend, float]]:
        """
        Step 2: Trend & Magnitude Validation for VRA executor.
        Input: trend_window (DataFrame) from min volume candle to max volume candle (inclusive).
        Returns:
            (Trend, magnitude): Tuple of trend direction and magnitude if all validations pass.
            None: If any validation fails.
        """
        # Validation 1: Magnitude threshold
        self.next_validation()
        window_size_val, window_trend = window_utils.get_window_size_and_trend(trend_window)
        if abs(window_size_val) < self.settings.min_trend_magnitude:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Trend magnitude did not meet threshold. Value: {window_size_val:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return (None, None)
        else:
            self.validations.append(Validation(
                name=nameof(self.settings.min_trend_magnitude),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Trend magnitude meets threshold. Value: {window_size_val:.2f}",
                status=ValidationStatus.PASSED
            ))

        # Validation 2: Open price extremes and their positions
        self.next_validation()
        trend_window_edge_size = self.settings.trend_window_edge_slice
        open_prices = trend_window['open']
        L_idx = open_prices.idxmin()
        H_idx = open_prices.idxmax()
        L_pos = trend_window.index.get_loc(L_idx)
        H_pos = trend_window.index.get_loc(H_idx)
        first_pos = 0
        last_pos = len(trend_window) - 1
        if window_trend == Trend.UPTREND:
            if not (L_pos < H_pos):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="In uptrend, L is not before H.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            # No Validation object for logic-only check
            if not (L_pos - first_pos <= trend_window_edge_size):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In uptrend, L is too far from start: {L_pos} > {trend_window_edge_size}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            else:
                self.validations.append(Validation(
                    name=nameof(self.settings.trend_window_edge_slice),
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In uptrend, L is near start: {L_pos} <= {trend_window_edge_size}",
                    status=ValidationStatus.PASSED
                ))
            if not (last_pos - H_pos <= trend_window_edge_size):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In uptrend, H is too far from end: {last_pos - H_pos} > {trend_window_edge_size}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            else:
                self.validations.append(Validation(
                    name=nameof(self.settings.trend_window_edge_slice),
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In uptrend, H is near end: {last_pos - H_pos} <= {trend_window_edge_size}",
                    status=ValidationStatus.PASSED
                ))
        elif window_trend == Trend.DOWNTREND:
            if not (H_pos < L_pos):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="In downtrend, H is not before L.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            # No Validation object for logic-only check
            if not (H_pos - first_pos <= trend_window_edge_size):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In downtrend, H is too far from start: {H_pos} > {trend_window_edge_size}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            else:
                self.validations.append(Validation(
                    name=nameof(self.settings.trend_window_edge_slice),
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In downtrend, H is near start: {H_pos} <= {trend_window_edge_size}",
                    status=ValidationStatus.PASSED
                ))
            if not (last_pos - L_pos <= trend_window_edge_size):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In downtrend, L is too far from end: {last_pos - L_pos} > {trend_window_edge_size}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            else:
                self.validations.append(Validation(
                    name=nameof(self.settings.trend_window_edge_slice),
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"In downtrend, L is near end: {last_pos - L_pos} <= {trend_window_edge_size}",
                    status=ValidationStatus.PASSED
                ))
        else:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Trend direction is not uptrend or downtrend.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return (None, None)
        
        return (window_trend, window_size_val)
