import pandas as pd
import logging
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Mode, Signal, ValidationStatus, LogLevel
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
        
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0

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
        
        df_indexed = df.reset_index()

        loop_end = len(df_indexed)
        min_scan_index = lookback_window_size
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            lookback_window_df = df_indexed.iloc[i - lookback_window_size : i]
            self.current_window_start_time = lookback_window_df.iloc[0]['time']
            self.current_window_end_time = lookback_window_df.iloc[-1]['time']

            consecutive_window_df = lookback_window_df.tail(consecutive_window_size)
            conditional_window_df = lookback_window_df.iloc[:-consecutive_window_size]

            # --- Step 1: Find and validate the consolidated candle ---
            self.current_step = 1
            
            # Pre-validation: All consecutive candles must have the same trend, determined by the last candle.
            last_candle_in_consecutive = consecutive_window_df.iloc[-1]
            last_candle_is_green = candle_utils.is_green_candle(last_candle_in_consecutive)
            
            if not all(candle_utils.is_green_candle(row) == last_candle_is_green for _, row in consecutive_window_df.iterrows()):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=1,
                    message="Consecutive candles do not have the same trend.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Pre-validation 2: Check min body size for each consecutive candle
            if not all(candle_utils.is_body_bigger_than_min(row, self.settings.min_consecutive_candle_body_size)[0] for _, row in consecutive_window_df.iterrows()):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation='1b',
                    message="Not all consecutive candles meet the minimum body size.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

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
                    validation=2,
                    message=f"Consolidated body ratio not thick enough. Ratio: {body_ratio:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            is_min_body_size, body_size = candle_utils.is_body_bigger_than_min(consolidated_candle, self.settings.min_consolidated_body_size)
            if not is_min_body_size:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=3,
                    message=f"Consolidated body size does not meet minimum. Size: {body_size:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            potential_signal = Signal.BUY if last_candle_is_green else Signal.SELL

            # --- Step 2: Cooldown Validation ---
            self.current_step += 1
            last_candle = candle_utils.get_last_candle(lookback_window_df)
            if last_candle is None: continue

            if is_in_cooldown(new_alert_time=last_candle['time'], new_signal=potential_signal, latest_alert=self.LATEST_ALERT, cooldown_window=self.settings.cooldown_window):
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

            # --- Step 3: Validate the conditional window ---
            self.current_step += 1
            if not all(candle_utils.is_body_smaller_than_max(row, self.settings.max_conditional_candle_body_size) for _, row in conditional_window_df.iterrows()):
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

            max_volume_in_conditional = candle_utils.find_max_volume_candle(conditional_window_df)
            min_volume_in_consecutive = candle_utils.find_min_volume_candle(consecutive_window_df)
            
            is_volume_confirmed, volume_ratio = candle_utils.validate_volume_ratio(large_volume_candle=min_volume_in_consecutive, small_volume_candle=max_volume_in_conditional, min_volume_multiplier=self.settings.volume_multiplier)
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
            
            # --- Step 4: Final Alert Confirmation (Breakout) ---
            self.current_step += 1
            if potential_signal == Signal.BUY:
                if last_candle['close'] < conditional_window_df['high'].max():
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
                if last_candle['close'] > conditional_window_df['low'].min():
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

            # --- Create and append alert ---
            alert_time = last_candle['time']
            alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
            details = {"consolidated_body_ratio": round(body_ratio, 2), "conditional_window_price_range": round(price_range, 2)}

            first_candle = candle_utils.get_first_candle(lookback_window_df)
            if first_candle is None: continue

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
