import pandas as pd
import logging
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Mode, Signal, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.utils import candle_utils
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.utils.log_factory import log
from .settings import ConsecutivePowerCandlesSettings


class ConsecutivePowerCandlesExecutor(Executor):
    APPROACH_NAME = Approach.CONSECUTIVE_POWER_CANDLES
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = ConsecutivePowerCandlesSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        try:
            if not df.empty:
                log(
                    logger=self.logger,
                    name=self.__class__.__name__,
                    step=0,
                    message=f"Running '{self.APPROACH_NAME}' for symbol {self.symbol}...",
                    log_level=LogLevel.INFO,
                    execution_symbol=self.symbol,
                    alert_time=df.iloc[-1]['time']
                )
            
            alerts_data = self._find_consecutive_power_candle_alerts(df, new_candle_count)
            
            if not df.empty:
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    step=0,
                    message=f"'{self.APPROACH_NAME}' for {self.symbol} found {len(alerts_data)} alerts.",
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

    def _find_consecutive_power_candle_alerts(self, df: pd.DataFrame, new_candle_count=0) -> list[AlertData]:
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        lookback_window_size = self.settings.lookback_window
        consecutive_window_size = self.settings.consecutive_window_size
        # --- Standardized loop setup ---
        # Use base class utility to prepare indexed DataFrame and loop boundaries
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            is_development_mode,
            df,
            new_candle_count,
            lookback_window_size
        )
        for i in range(loop_end, loop_start - 1, -1):
            # --- Standardized window context extraction ---
            # Use base class utility to extract lookback window, boundary candles, and context variables
            (
                lookback_window_df,
                first_candle,
                last_candle,
                self.current_window_start_time,
                self.current_window_end_time,
                self.current_step
            ) = self.get_window_context(
                i,
                df_indexed,
                lookback_window_size
            )

            consecutive_window_df = lookback_window_df.tail(consecutive_window_size)
            conditional_window_df = lookback_window_df.iloc[:-consecutive_window_size]
            if first_candle is None:
                continue
            if last_candle is None:
                continue

            # Step 1: All consecutive candles must have the same trend
            self.next_step()
            last_candle_in_consecutive = consecutive_window_df.iloc[-1]
            last_candle_is_green = candle_utils.is_green_candle(last_candle_in_consecutive)

            # Validation 1: All consecutive candles must have the same trend
            if not all(candle_utils.is_green_candle(row) == last_candle_is_green for _, row in consecutive_window_df.iterrows()):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Consecutive candles do not have the same trend.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation 2: Check min body size for each consecutive candle
            self.validation_step += 1
            if not all(candle_utils.is_body_bigger_than_min(row, self.settings.min_consecutive_candle_body_size)[0] for _, row in consecutive_window_df.iterrows()):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Not all consecutive candles meet the minimum body size.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            # Validation 3: Consolidated candle checks
            self.validation_step += 1
            consolidated_candle = candle_utils.create_consolidated_candle(consecutive_window_df)
            if consolidated_candle is None:
                continue
            is_thick_body, body_ratio = candle_utils.is_body_ratio_bigger_than_min(consolidated_candle, self.settings.min_consolidated_body_ratio)
            if not is_thick_body:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Consolidated body ratio not thick enough. Ratio: {body_ratio:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            self.validation_step += 1
            is_min_body_size, body_size = candle_utils.is_body_bigger_than_min(consolidated_candle, self.settings.min_consolidated_body_size)
            if not is_min_body_size:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Consolidated body size does not meet minimum. Size: {body_size:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation 4: Each consecutive candle's volume <= pre-candle (last of conditional window) * max_volume_multiplier
            self.validation_step += 1
            pre_candle = conditional_window_df.iloc[-1]
            max_volume = pre_candle['volume'] * self.settings.max_volume_multiplier
            over_volume_candles = [row for _, row in consecutive_window_df.iterrows() if row['volume'] > max_volume]
            if over_volume_candles:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"One or more consecutive candles have volume greater than pre-candle volume {pre_candle['volume']} * max_volume_multiplier {self.settings.max_volume_multiplier}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            potential_signal = Signal.BUY if last_candle_is_green else Signal.SELL
            # Step 2: Cooldown Validation
            if is_in_cooldown(new_alert_time=last_candle['time'], new_signal=potential_signal, latest_alert=self.LATEST_ALERT, cooldown_window=self.settings.cooldown_window):
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
                continue

            # Step 3: Conditional window validations (mirrored from Strong Candle)
            self.next_step()
            # Validation 1: Open price extremes and their positions
            window_size_val, window_trend = self._validate_open_extremes(conditional_window_df)
            if window_size_val is None or window_trend is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Open price extremes validation failed.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            # Validation 2: Window trend and consolidated candle color consistency
            self.validation_step += 1
            if not candle_utils.is_candle_trend_consistent(consolidated_candle, window_trend):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Window trend and consolidated candle color are not consistent.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            # Validation 3: Conditional price range threshold
            self.validation_step += 1
            if window_size_val > self.settings.max_difference_price_threshold:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Conditional price range {window_size_val} exceeds threshold.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            # Validation 4: All conditional candles have small bodies
            self.validation_step += 1
            all_small_bodies = all(
                candle_utils.is_body_smaller_than_max(row, self.settings.max_conditional_candle_body_size)
                for _, row in conditional_window_df.iterrows()
            )
            if not all_small_bodies:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Not all conditional candles have small bodies.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            # Step 4: Final Alert Confirmation
            self.next_step()
            self.validation_step = 1
            if potential_signal == Signal.BUY:
                if last_candle['close'] < conditional_window_df['high'].max():
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message="Uptrend alert confirmation failed: close is not above conditional high.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue
            elif potential_signal == Signal.SELL:
                if last_candle['close'] > conditional_window_df['low'].min():
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message="Downtrend alert confirmation failed: close is not below conditional low.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue
            # Create and append alert
            alert_time = last_candle['time']
            alert_id = str(int(alert_time.timestamp()))
            details = {
                "consolidated_body_ratio": round(body_ratio, 2),
                "conditional_window_price_range": round(window_size_val, 2),
                "first_candle_time": first_candle['time'].isoformat(),
                "last_candle_time": last_candle['time'].isoformat(),
                "step1_body_ratio": round(body_ratio, 2),
                "step1_body_size": round(body_size, 2),
                "step3_price_range": round(window_size_val, 2)
            }
            alert_data = AlertData(
                approach=self.APPROACH_NAME,
                id=alert_id,
                symbol=self.symbol,
                signal=potential_signal,
                alert_price=last_candle['close'],
                alert_time=alert_time,
                start_price=first_candle['open'],
                start_time=first_candle['time'],
                magnitude=body_size,
                details=json.dumps(details)
            )
            alerts.append(alert_data)
            self.LATEST_ALERT = alert_data
            if not is_development_mode:
                return alerts
        return alerts[::-1]
    
    def _validate_open_extremes(self, window_df: pd.DataFrame) -> Optional[tuple[float, Trend]]:
        n = self.settings.trend_window_edge_slice
        open_prices = window_df['open']
        L_idx = open_prices.idxmin()
        H_idx = open_prices.idxmax()
        L_pos = window_df.index.get_loc(L_idx)
        H_pos = window_df.index.get_loc(H_idx)
        first_pos = 0
        last_pos = len(window_df) - 1
        from src.stockreports.utils import window_utils
        window_size_val, window_trend = window_utils.get_window_size_and_trend(window_df)
        self.validation_step += 1

        if window_trend is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Open extremes validation failed: could not determine trend.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return (None, None)
        if window_trend == Trend.UPTREND:
            if not (L_pos < H_pos):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Open extremes validation failed: L is not before H in uptrend.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            if not (L_pos - first_pos <= n):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Open extremes validation failed: L is too far from start in uptrend: {L_pos} > {n}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            if not (last_pos - H_pos <= n):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Open extremes validation failed: H is too far from end in uptrend: {last_pos - H_pos} > {n}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
        elif window_trend == Trend.DOWNTREND:
            if not (H_pos < L_pos):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Open extremes validation failed: H is not before L in downtrend.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            if not (H_pos - first_pos <= n):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Open extremes validation failed: H is too far from start in downtrend: {H_pos} > {n}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
            if not (last_pos - L_pos <= n):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Open extremes validation failed: L is too far from end in downtrend: {last_pos - L_pos} > {n}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                return (None, None)
        else:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Open extremes validation failed: unknown trend direction.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return (None, None)
        return (window_size_val, window_trend)

