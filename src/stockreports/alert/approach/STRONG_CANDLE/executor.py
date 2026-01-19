# src/stockreports/alert/approach/STRONG_CANDLE/executor.py
import pandas as pd
import logging
import json
from typing import Optional

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Mode, Signal, ValidationStatus, LogLevel
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.utils import candle_utils
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.utils.log_factory import log
from .settings import StrongCandleSettings


class StrongCandleExecutor(Executor):
    APPROACH_NAME = Approach.STRONG_CANDLE
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = StrongCandleSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)
        
        # Initialize context variables
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the Strong Candle approach. It identifies a strong candle
        followed by a confirmation of a conditional window.
        """
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
            
            alerts_data = self._find_strong_candle_alerts(df, new_candle_count)
            
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

    def _find_strong_candle_alerts(self, df: pd.DataFrame, new_candle_count=0) -> list[AlertData]:
        """
        Finds alerts based on a state machine pattern, using a unified reverse loop.
        This function is optimized for both DEPLOYMENT (latest alert) and DEVELOPMENT (all alerts) modes.
        """
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        lookback_window_size = self.settings.lookback_window
        
        df_indexed = df.reset_index()

        loop_end = len(df_indexed)
        min_scan_index = lookback_window_size
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            # --- Reset context for the new window ---
            lookback_window_df = df_indexed.iloc[i - lookback_window_size : i]
            self.current_window_start_time = lookback_window_df.iloc[0]['time']
            self.current_window_end_time = lookback_window_df.iloc[-1]['time']

            # --- Step 1: Find and validate the strong candle 'A' (Cheapest checks first) ---
            self.current_step = 1
            strong_candle = candle_utils.get_last_candle(lookback_window_df)
            if strong_candle is None:
                continue

            is_thick_body, body_ratio = candle_utils.is_body_ratio_bigger_than_min(strong_candle, self.settings.min_body_ratio)
            if not is_thick_body:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=1,
                    message=f"Body ratio is not thick enough. Ratio: {body_ratio:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            is_min_body_size, body_size = candle_utils.is_body_bigger_than_min(strong_candle, self.settings.min_body_size)
            if not is_min_body_size:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=2,
                    message=f"Body size does not meet minimum. Size: {body_size:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            is_uptrend = candle_utils.is_green_candle(strong_candle)
            is_downtrend = candle_utils.is_red_candle(strong_candle)
            
            potential_signal = None
            if is_uptrend:
                potential_signal = Signal.BUY
            elif is_downtrend:
                potential_signal = Signal.SELL
            else:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=3,
                    message="No clear trend direction for strong candle.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="Strong candle validated.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )

            # --- Step 2: Cooldown Validation (Cheap check) ---
            self.current_step += 1
            if is_in_cooldown(
                new_alert_time=strong_candle['time'],
                new_signal=potential_signal,
                latest_alert=StrongCandleExecutor.LATEST_ALERT,
                cooldown_window=self.settings.cooldown_window
            ):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Alert is in cooldown period.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="Cooldown check passed.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )

            # --- Step 3: Validate the conditional window (More expensive checks) ---
            self.current_step += 1
            conditional_window_df = lookback_window_df.iloc[:-1]
            
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
                    validation=1,
                    message="Not all conditional candles have small bodies.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            price_range = conditional_window_df['high'].max() - conditional_window_df['low'].min()
            if price_range > self.settings.max_difference_price_threshold:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=2,
                    message=f"Conditional price range {price_range} exceeds threshold.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            max_volume_candle_in_conditional = candle_utils.find_max_volume_candle(conditional_window_df)
            is_volume_confirmed, volume_ratio = candle_utils.validate_volume_ratio(
                large_volume_candle=strong_candle,
                small_volume_candle=max_volume_candle_in_conditional,
                min_volume_multiplier=self.settings.volume_multiplier
            )
            if not is_volume_confirmed:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=3,
                    message=f"Volume confirmation failed. Ratio: {volume_ratio:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="Conditional window validated.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )

            # --- Step 4: Final Alert Confirmation (Breakout) ---
            self.current_step += 1
            if potential_signal == Signal.BUY:
                if strong_candle['close'] < conditional_window_df['high'].max():
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=1,
                        message="Uptrend alert confirmation failed: close is not above conditional high.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue
            elif potential_signal == Signal.SELL:
                if strong_candle['close'] > conditional_window_df['low'].min():
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=2,
                        message="Downtrend alert confirmation failed: close is not below conditional low.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue
            
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="Alert trend confirmed.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )

            # --- Create and append alert ---
            alert_time = strong_candle['time']
            alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

            details = {
                "strong_candle_time": strong_candle['time'].isoformat(),
                "strong_candle_body_ratio": round(body_ratio, 2),
                "conditional_window_price_range": round(price_range, 2)
            }

            alert_data = AlertData(
                approach=self.APPROACH_NAME,
                id=alert_id,
                symbol=self.symbol,
                signal=potential_signal,
                alert_price=strong_candle['close'],
                alert_time=alert_time,
                start_price=strong_candle['open'],
                start_time=strong_candle['time'],
                magnitude=body_size,
                details=json.dumps(details)
            )
            alerts.append(alert_data)
            StrongCandleExecutor.LATEST_ALERT = alert_data

            if not is_development_mode:
                return alerts
                
        return alerts[::-1]
