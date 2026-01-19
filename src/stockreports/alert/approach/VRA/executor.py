import pandas as pd
import logging
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertResult, AlertData
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

        loop_end_index = len(df_indexed) - 1
        min_scan_index = window_size - 1

        if is_development_mode:
            loop_start_index = min_scan_index
        else:
            loop_start_index = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end_index, loop_start_index - 1, -1):
            window_start_index = i - window_size + 1
            window_df = df_indexed.iloc[window_start_index : i + 1].copy()
            self.current_window_end_time = window_df.iloc[-1]['time']
            self.current_window_start_time = window_df.iloc[0]['time']
            
            # Step 1: Trend & Magnitude Validation
            self.current_step = 1
            
            # Get size and trend from the initial, full window
            initial_window_size_val, initial_trend = window_utils.get_window_size_and_trend(window_df)

            if initial_trend is None:
                continue

            # Now, find the appropriate peak or trough to measure the true magnitude from
            magnitude_window = None
            if initial_trend == Trend.UPTREND:
                lowest_trough_result = window_utils.get_lowest_trough(window_df)
                if lowest_trough_result:
                    lowest_trough, _ = lowest_trough_result
                    magnitude_window = window_df.loc[lowest_trough.name:].copy()
            elif initial_trend == Trend.DOWNTREND:
                highest_peak_result = window_utils.get_highest_peak(window_df)
                if highest_peak_result:
                    highest_peak, _ = highest_peak_result
                    magnitude_window = window_df.loc[highest_peak.name:].copy()

            # Recalculate size and trend on the more accurate magnitude window, if available
            window_size_val = 0.0
            window_trend = initial_trend # Default to initial trend
            if magnitude_window is not None and not magnitude_window.empty:
                window_size_val, window_trend = window_utils.get_window_size_and_trend(magnitude_window)

            # The validation passes if either the initial window or the refined magnitude window meets the threshold
            is_initial_magnitude_valid = abs(initial_window_size_val) >= self.settings.min_trend_magnitude
            is_refined_magnitude_valid = abs(window_size_val) >= self.settings.min_trend_magnitude

            if not (is_initial_magnitude_valid or is_refined_magnitude_valid):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Trend magnitude did not meet threshold. Initial: {abs(initial_window_size_val):.2f}, Refined: {abs(window_size_val):.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            original_signal = Signal.BUY if window_trend == Trend.UPTREND else Signal.SELL

            # Step 2: Volume Validation
            self.current_step += 1
            max_vol_candle = candle_utils.find_max_volume_candle(window_df)
            min_vol_candle = candle_utils.find_min_volume_candle(window_df)

            is_volume_ratio_valid, volume_ratio = candle_utils.validate_volume_ratio(max_vol_candle, min_vol_candle, self.settings.volume_multiplier)
            if not is_volume_ratio_valid:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=1,
                    message=f"Volume ratio is not significant enough. Ratio: {volume_ratio:.2f}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            if min_vol_candle.name >= max_vol_candle.name:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Min volume candle did not occur before max volume candle.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Step 3: Reversal Confirmation
            self.current_step += 1
            confirmation_window = window_df.loc[max_vol_candle.name:].copy()
            alert_candle = candle_utils.get_last_candle(confirmation_window)

            if alert_candle is None:
                continue

            # Validation A: Alert candle is the biggest body in the confirmation window
            biggest_body_in_confirmation = candle_utils.find_biggest_body_candle(confirmation_window)
            if alert_candle.name != biggest_body_in_confirmation.name:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Alert candle is not the biggest body candle in the confirmation window.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation B: Alert candle body size is sufficient
            is_body_big_enough, body_size = candle_utils.is_body_bigger_than_min(alert_candle, self.settings.min_alert_body_size)
            if not is_body_big_enough:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Alert candle body size ({body_size:.2f}) is not bigger than min size ({self.settings.min_alert_body_size}).",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation C: Alert candle color matches trend
            is_uptrend = window_trend == Trend.UPTREND
            is_correct_color = (is_uptrend and candle_utils.is_green_candle(alert_candle)) or \
                               (not is_uptrend and candle_utils.is_red_candle(alert_candle))

            if not is_correct_color:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Alert candle color does not match the window trend ({window_trend}).",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # --- All primary validations passed, define reversal signal ---
            reversal_signal = Signal.SELL if original_signal == Signal.BUY else Signal.BUY
            
            # --- Final Checks using Reversal Signal ---
            self.current_step += 1
            
            # Cooldown Check
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
                    message="Alert is in cooldown period.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            alert_candle = candle_utils.get_last_candle(window_df)
            if alert_candle is None:
                continue
            
            first_candle = candle_utils.get_first_candle(window_df)
            if first_candle is None:
                continue

            alert_id = f"{self.symbol}_{self.APPROACH_NAME}_{self.current_window_end_time.strftime('%Y%m%d%H%M%S')}"

            alert_data = AlertData(
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
                    "max_volume_candle_time": str(max_vol_candle.name),
                    "min_volume_candle_time": str(min_vol_candle.name)
                })
            )
            alerts.append(alert_data)
            VraExecutor.LATEST_ALERT = alert_data

        return alerts
