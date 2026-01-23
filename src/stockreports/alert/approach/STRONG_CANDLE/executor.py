# src/stockreports/alert/approach/STRONG_CANDLE/executor.py
import pandas as pd
import logging
import json
from typing import Optional

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Mode, Signal, ValidationStatus, LogLevel, Trend
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

        # Stores Validation objects for each validation passed at each step
        validations: list = []             

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

            first_candle = candle_utils.get_first_candle(lookback_window_df)

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

            self.validation_step += 1
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

            # --- Last Validation in Step 1: Volume of strong candle <= previous candle * max_volume_multiplier ---
            self.validation_step += 1
            prev_idx = -2  # strong_candle is always the last row in lookback_window_df
            prev_candle = lookback_window_df.iloc[prev_idx]
            max_volume = prev_candle['volume'] * self.settings.max_volume_multiplier
            if strong_candle['volume'] > max_volume:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Strong candle volume {strong_candle['volume']} exceeds previous candle volume {prev_candle['volume']} * max_volume_multiplier {self.settings.max_volume_multiplier}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # --- Step 2: Cooldown Validation (Cheap check) ---
            self.next_step()
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

            # --- Step 3: Validate the conditional window (More expensive checks) ---
            self.current_step += 1
            self.validation_step = 1
            conditional_window_df = lookback_window_df.iloc[:-1]

            # Validation: Open price extremes and their positions (copied from VRA)
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

            # New Validation: Window trend and strong candle color must be consistent
            self.validation_step += 1
            if not candle_utils.is_candle_trend_consistent(strong_candle, window_trend):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="Window trend and strong candle color are not consistent.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            
            if window_size_val > self.settings.max_difference_price_threshold:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=2,
                    message=f"Conditional price range {window_size_val} exceeds threshold.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

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
                    validation=1,
                    message="Not all conditional candles have small bodies.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # max_volume_candle_in_conditional = candle_utils.find_max_volume_candle(conditional_window_df)
            # is_volume_confirmed, volume_ratio = candle_utils.validate_volume_ratio(
            #     large_volume_candle=strong_candle,
            #     small_volume_candle=max_volume_candle_in_conditional,
            #     min_volume_multiplier=self.settings.volume_multiplier
            # )
            # if not is_volume_confirmed:
            #     log(
            #         logger=self.logger,
            #         status=ValidationStatus.FAILED,
            #         name=self.__class__.__name__,
            #         alert_time=self.current_window_end_time,
            #         step=self.current_step,
            #         validation=3,
            #         message=f"Volume confirmation failed. Ratio: {volume_ratio:.2f}",
            #         log_level=LogLevel.DEBUG,
            #         execution_symbol=self.symbol,
            #         start_time=self.current_window_start_time,
            #         end_time=self.current_window_end_time
            #     )
            #     continue

            # --- Step 4: Final Alert Confirmation (Breakout) ---
            self.current_step += 1
            self.validation_step = 1
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

            # --- Create and append alert ---
            alert_time = strong_candle['time']
            alert_id = str(int(alert_time.timestamp()))

            details = {
                "strong_candle_time": strong_candle['time'].isoformat(),
                "strong_candle_body_ratio": round(body_ratio, 2),
                "conditional_window_price_range": round(window_size_val, 2)
            }

            alert_data = AlertData(
                approach=self.APPROACH_NAME,
                id=alert_id,
                symbol=self.symbol,
                signal=potential_signal,
                alert_price=strong_candle['close'],
                alert_time=alert_time,
                start_price=first_candle['open'],
                start_time=first_candle['time'],
                magnitude=body_size,
                details=json.dumps(details)
            )
            alerts.append(alert_data)
            StrongCandleExecutor.LATEST_ALERT = alert_data

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
