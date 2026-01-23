import pandas as pd
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Signal, Trend, ValidationStatus, LogLevel, Mode
from src.stockreports.utils.candle_utils import (
    find_max_volume_candle,
    is_green_candle,
    find_min_volume_candle,
    validate_volume_ratio,
    find_biggest_body_candle,
    get_candle_body_size,
    is_candle_trend_consistent
)
from src.stockreports.utils.window_utils import get_window_by_trend
from src.stockreports.utils.log_factory import log
from src.stockreports.utils.alert_utils import is_in_cooldown
from .settings import MomentumExhaustionSettings


class MomentumExhaustionExecutor(Executor):
    APPROACH_NAME = Approach.MOMENTUM_EXHAUSTION
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = MomentumExhaustionSettings(symbol)
        super().__init__(symbol, self.settings)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        try:
            log(
                logger=self.logger,
                name=self.APPROACH_NAME,
                status=ValidationStatus.IN_PROGRESS,
                alert_time="N/A",
                step=0,
                message=f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol
            )
            
            alerts_data = self._find_momentum_exhaustion_alerts(df, new_candle_count)
            
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.APPROACH_NAME,
                alert_time="N/A",
                step=0,
                message=f"'{self.APPROACH_NAME}' approach found {len(alerts_data)} alerts.",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol
            )

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time="N/A",
                step=0,
                message=f"An error occurred during '{self.APPROACH_NAME}' execution: {e}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol
            )
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=pd.DataFrame(),
                status="FAILED",
                message=str(e)
            )

    def _find_momentum_exhaustion_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        alerts = []
        required_lookback = self.settings.lookback_window
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT

        df_indexed = df.set_index('time')
        
        loop_end = len(df_indexed)
        min_scan_index = required_lookback

        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)


        for i in range(loop_start, loop_end + 1):
            window = df_indexed.iloc[i - required_lookback : i]
            self.current_window_start_time = window.index[0]
            self.current_window_end_time = window.index[-1]
            self.current_step = 0

            # Pre-validation - Ensure the first candle of the window is after 09:30:00
            if self.current_window_start_time.time() < pd.to_datetime("09:30:00").time():
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.APPROACH_NAME,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Skipping window because its start time {self.current_window_start_time.time()} is before 09:30:00.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            alert = self._analyze_window(window)
            
            if alert:
                alerts.append(alert)
                MomentumExhaustionExecutor.LATEST_ALERT = alert

        return alerts

    def _analyze_window(self, window_df: pd.DataFrame) -> Optional[AlertData]:
        # Reset step counter for the new window analysis
        # Step 1: Find the candle with the maximum volume in the window (excluding the last candle)
        self.current_step = 1
        analysis_window = window_df.iloc[:-1]
        max_volume_candle = find_max_volume_candle(analysis_window)
        
        try:
            max_volume_candle_index = analysis_window.index.get_loc(max_volume_candle.name)
        except KeyError:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="Could not locate max volume candle in window index.",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
        
        # Step 2: Determine trend and check for cooldown
        self.current_step += 1
        self.validation_step = 1
        trend = Trend.UPTREND if is_green_candle(max_volume_candle) else Trend.DOWNTREND
        potential_reversed_signal = Signal.SELL if trend == Trend.UPTREND else Signal.BUY

        if is_in_cooldown(
            new_alert_time=self.current_window_end_time,
            new_signal=potential_reversed_signal,
            latest_alert=MomentumExhaustionExecutor.LATEST_ALERT,
            cooldown_window=self.settings.cooldown_window
        ):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Alert is in cooldown period.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Step 3: Ensure there are pre and post windows to analyze
        self.current_step += 1
        self.validation_step = 1
        first_valid_index = 1 # Must have at least one candle in pre_window
        last_valid_index = len(analysis_window) - 3 # Must have at least two candles in post_window
        
        if not (first_valid_index <= max_volume_candle_index <= last_valid_index):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Max volume candle is at the edge, cannot form pre/post windows.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        pre_window = analysis_window.iloc[:max_volume_candle_index]
        post_window = analysis_window.iloc[max_volume_candle_index + 1:]
        reversal_candle = window_df.iloc[-1]

        # Step 4: Validate post-window price proximity
        self.current_step += 1
        self.validation_step = 1
        post_window_prices = pd.concat([post_window['open'], post_window['close']])
        highest_price_in_post = post_window_prices.max()
        lowest_price_in_post = post_window_prices.min()

        diff_to_high = abs(max_volume_candle['close'] - highest_price_in_post)
        diff_to_low = abs(max_volume_candle['close'] - lowest_price_in_post)

        if not (diff_to_high <= self.settings.post_climax_price_proximity_threshold or 
                diff_to_low <= self.settings.post_climax_price_proximity_threshold):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Post-window price proximity check failed. Diff to high: {diff_to_high:.2f}, Diff to low: {diff_to_low:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Step 5: Validate Pre-Window Conditions
        self.current_step += 1
        self.validation_step = 1

        # Validation 5.1: Check for sufficient candles
        if len(pre_window) < 2:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Not enough candles in pre window for analysis.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
        
        self.validation_step += 1
        # Validation 5.2: Max volume candle body size vs. biggest body in pre-window
        biggest_body_pre_window_candle = find_biggest_body_candle(pre_window)
        max_volume_candle_body_size = get_candle_body_size(max_volume_candle)
        biggest_pre_window_body_size = get_candle_body_size(biggest_body_pre_window_candle)

        if not (biggest_pre_window_body_size >= max_volume_candle_body_size):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=(
                    f"Max volume candle body size ({max_volume_candle_body_size:.2f}) is larger than the "
                    f"biggest body in pre-window ({biggest_pre_window_body_size:.2f})."
                ),
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        consolidated_trend_window = get_window_by_trend(pre_window, expected_trend=trend)

        self.validation_step += 1
        # Validation 5.3: Check for trend-consistent candles
        if consolidated_trend_window.empty or len(consolidated_trend_window) < 1:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Pre-climax window contains no candles matching the exhaustion trend.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        self.validation_step += 1
        # Validation 5.4: Compare climax volume to pre-window min volume
        min_volume_candle_in_pre_trend = find_min_volume_candle(consolidated_trend_window)
        is_volume_significant, pre_volume_ratio = validate_volume_ratio(
            large_volume_candle=max_volume_candle,
            small_volume_candle=min_volume_candle_in_pre_trend,
            min_volume_multiplier=self.settings.pre_window_volume_multiplier
        )
        
        if not is_volume_significant:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Max volume not significant compared to min volume in pre-trend window. Ratio: {pre_volume_ratio:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Step 6: Validate Post-Window Volume
        self.current_step += 1
        self.validation_step = 1
        min_volume_candle_in_post_trend = find_min_volume_candle(post_window)

        is_post_volume_significant, post_volume_ratio = validate_volume_ratio(
            large_volume_candle=max_volume_candle,
            small_volume_candle=min_volume_candle_in_post_trend,
            min_volume_multiplier=self.settings.post_window_volume_multiplier
        )

        if not is_post_volume_significant:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Max volume not significant compared to min volume in post-trend window. Ratio: {post_volume_ratio:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Step 7: Validate Reversal Candle
        self.current_step += 1
        self.validation_step = 1
        
        # Validation 7.1: Validate reversal candle trend consistency
        expected_reversal_trend = Trend.DOWNTREND if potential_reversed_signal == Signal.SELL else Trend.UPTREND
        if not is_candle_trend_consistent(reversal_candle, expected_reversal_trend):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Reversal candle trend is not consistent with the expected signal. Expected: {expected_reversal_trend}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        self.validation_step += 1
        # Validation 7.2: Validate reversal candle volume
        is_reversal_volume_significant, reversal_volume_ratio = validate_volume_ratio(
            large_volume_candle=reversal_candle,
            small_volume_candle=min_volume_candle_in_post_trend,
            min_volume_multiplier=self.settings.reversal_volume_multiplier
        )

        if not is_reversal_volume_significant:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.APPROACH_NAME,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Reversal candle volume not significant compared to min volume in post-trend. Ratio: {reversal_volume_ratio:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # All validations passed. Create alert data.
        return self._create_alert_data(
            signal=potential_reversed_signal,
            reversal_candle=reversal_candle,
            start_candle=window_df.iloc[0],
            trend=trend,
            max_volume_candle=max_volume_candle,
            ratios={
                "pre_volume_ratio": pre_volume_ratio,
                "post_volume_ratio": post_volume_ratio,
                "reversal_volume_ratio": reversal_volume_ratio,
            }
        )

    def _create_alert_data(
        self,
        signal: Signal,
        reversal_candle: pd.Series,
        start_candle: pd.Series,
        trend: Trend,
        max_volume_candle: pd.Series,
        ratios: dict
    ) -> AlertData:
        """Encapsulates the creation of the AlertData object."""
        
        alert_id = str(int(reversal_candle.name.timestamp()))
        magnitude = abs(reversal_candle['close'] - start_candle['open'])

        details = {
            "reason": "Reversal after volume climax and exhaustion.",
            "trend_at_climax": trend,
            "climax_candle_time": str(max_volume_candle.name),
            "pre_volume_ratio": round(ratios["pre_volume_ratio"], 2),
            "post_volume_ratio": round(ratios["post_volume_ratio"], 2),
            "reversal_volume_ratio": round(ratios["reversal_volume_ratio"], 2),
        }

        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            approach=self.APPROACH_NAME,
            signal=signal,
            alert_price=reversal_candle['close'],
            alert_time=reversal_candle.name,
            start_price=start_candle['open'],
            start_time=start_candle.name,
            magnitude=magnitude,
            details=json.dumps(details)
        )
