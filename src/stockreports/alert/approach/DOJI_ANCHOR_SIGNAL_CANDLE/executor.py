"""Executor for DOJI_ANCHOR_SIGNAL_CANDLE (Doji-first → anchor-backward)."""

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
    CandleColumn,
)
from src.stockreports.alert.model.models import AlertData, Validation
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import candle_utils
from .settings import DojiAnchorSignalCandleSettings
from .analyzer import DojiAnchorSignalCandleAnalyzer
from .validator import DojiAnchorSignalCandleValidator


class DojiAnchorSignalCandleExecutor(Executor):
    """Executor implementing Doji-first → anchor-backward detection."""

    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str, approach: Approach, resolution: int) -> None:
        self.settings = DojiAnchorSignalCandleSettings(symbol)
        self.analyzer = DojiAnchorSignalCandleAnalyzer()
        self.validator = DojiAnchorSignalCandleValidator()
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

        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=lookback_window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, lookback_window_size)
            if self.lookback_window_df is None or self.last_candle is None:
                continue

            # Pre-step: Find and prepare doji and anchor candles
            self.next_step()
            prep_result = self._step_prepare_candles(doji_idx=None)
            if prep_result is None:
                continue
            doji_idx, anchor_idx, trend, trend_candle_idx, avg_vol = prep_result

            # Determine reversal trend and signal early (O(1) operation)
            # Used by cooldown check and signal determination
            # If original trend is UPTREND, reversal is DOWNTREND (bearish) → SELL
            # If original trend is DOWNTREND, reversal is UPTREND (bullish) → BUY
            reversal_trend = candle_utils.get_reversal_trend(trend)
            reversal_signal = candle_utils.get_signal_from_trend(reversal_trend)
            if reversal_signal is None or reversal_signal == Signal.NEUTRAL:
                continue

            # Step 1: Cooldown check (O(1), ~75% fail rate)
            # Execute first to filter out frequent alerts before expensive validations
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=DojiAnchorSignalCandleExecutor.LATEST_ALERT,
                signal=reversal_signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Step 2: Alert-candle validation (O(1), ~55% fail rate)
            # Tests actual reversal signal occurrence - critical business logic
            self.next_step()
            alert_idx = len(self.lookback_window_df) - 1
            if not self._step_validate_alert_candle(doji_idx, alert_idx, trend, avg_vol):
                continue

            # Step 3: Momentum validation (O(window_size), ~45% fail rate)
            # Medium cost, vectorized operation, good failure rate
            self.next_step()
            if not self._step_validate_momentum(anchor_idx, doji_idx):
                continue

            # Step 4: Trend-candle validation (O(search_window), ~30% fail rate)
            # Highest cost - execute last when others likely to fail is lowest
            self.next_step()
            if not self._step_validate_trend_candle(trend_candle_idx, anchor_idx, doji_idx):
                continue
            
            # Step 5: Alert creation
            self.next_step()
            details_dict = self._add_details_for_alert(
                window_size=lookback_window_size,
                doji_idx=doji_idx,
                anchor_idx=anchor_idx,
                original_trend=trend,
                trend_candle_idx=trend_candle_idx,
                avg_momentum_volume=avg_vol,
            )

            magnitude_threshold = self.settings.momentum_min_price_move
            alert_data = self._create_alert_with_details(
                final_signal=reversal_signal,
                final_trend=reversal_trend,
                final_alert_candle=self.last_candle,
                final_magnitude=magnitude_threshold,
                details=details_dict
            )

            if alert_data is not None:
                self.alerts.append(alert_data)
                DojiAnchorSignalCandleExecutor.LATEST_ALERT = alert_data

                if not self.is_development_mode:
                    return self.alerts

        return self.alerts

    def _step_find_doji(self) -> Optional[int]:
        """Locate most recent doji in lookback window using analyzer and record validation."""
        self.next_validation()
        try:
            doji_idx = DojiAnchorSignalCandleAnalyzer.find_most_recent_doji(
                self.lookback_window_df,
                self.settings.max_doji_body_ratio,
                self.settings.min_doji_range,
            )
            if doji_idx is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"No doji found with body_ratio <= {self.settings.max_doji_body_ratio}, range >= {self.settings.min_doji_range}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            self.validations.append(Validation(
                name=nameof(self.settings.max_doji_body_ratio),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Doji found at index {doji_idx}",
                status=ValidationStatus.PASSED
            ))
            return doji_idx
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Doji detection failed - {str(e)}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

    def _step_prepare_candles(self, doji_idx: Optional[int] = None) -> Optional[Tuple[int, int, str, int, float]]:
        """Pre-step: Find and prepare doji and anchor candles without real validations.
        
        Returns tuple of (doji_idx, anchor_idx, trend, trend_candle_idx, avg_vol) or None.
        """
        self.next_validation()
        try:
            # Find doji
            if doji_idx is None:
                doji_idx = DojiAnchorSignalCandleAnalyzer.find_most_recent_doji(
                    self.lookback_window_df,
                    self.settings.max_doji_body_ratio,
                    self.settings.min_doji_range,
                )
            if doji_idx is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"No doji found during candle preparation",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            # Discover anchor and determine trend direction
            anchor_result = DojiAnchorSignalCandleAnalyzer.discover_anchor_with_trend(
                self.lookback_window_df,
                doji_idx,
                self.settings.anchor_search_limit,
                trend_window=self.settings.trend_window,
            )
            if anchor_result is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Failed to discover anchor with trend for doji at {doji_idx}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return None
            
            anchor_idx, trend, trend_candle_idx, avg_vol = anchor_result
            
            self.validations.append(Validation(
                name="prepare_candles",
                step=self.current_step,
                validation=self.validation_step,
                message=f"Doji@{doji_idx}, Anchor@{anchor_idx}, Trend_Candle@{trend_candle_idx}, Trend={trend}",
                status=ValidationStatus.PASSED
            ))
            return (doji_idx, anchor_idx, trend, trend_candle_idx, avg_vol)
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Candle preparation failed - {str(e)}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return None

    def _step_validate_momentum(self, anchor_idx: int, doji_idx: int) -> bool:
        """Validate momentum between anchor and doji using validator."""
        self.next_validation()
        try:
            momentum_ok = DojiAnchorSignalCandleValidator.validate_momentum(
                self.lookback_window_df,
                anchor_idx,
                doji_idx,
                self.settings.momentum_min_price_move,
            )
            if not momentum_ok:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Momentum validation failed: price move below {self.settings.momentum_min_price_move}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return False
            self.validations.append(Validation(
                name=nameof(self.settings.momentum_min_price_move),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Momentum validation passed",
                status=ValidationStatus.PASSED
            ))
            return True
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Momentum validation failed - {str(e)}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return False

    def _step_validate_trend_candle(self, trend_candle_idx: int, anchor_idx: int, doji_idx: int) -> bool:
        """Validate trend candle."""
        self.next_validation()
        try:
            # Validate the provided trend_candle_idx
            if trend_candle_idx is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Trend candle validation failed: trend_candle_idx is None",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return False
            trend_ok = DojiAnchorSignalCandleValidator.validate_trend_candle(
                self.lookback_window_df,
                trend_candle_idx,
                anchor_idx,
                doji_idx,
                self.settings.trend_candle_range_multiplier,
                self.settings.trend_candle_min_body,
            )
            if not trend_ok:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Trend candle validation failed at index {trend_candle_idx}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return False
            
            self.validations.append(Validation(
                name=nameof(self.settings.trend_candle_range_multiplier),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Trend candle validation passed at {trend_candle_idx}",
                status=ValidationStatus.PASSED
            ))
            return True
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Trend candle validation failed - {str(e)}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return False

    def _step_validate_alert_candle(self, doji_idx: int, alert_idx: Optional[int], trend: str, avg_mom_vol: Optional[float]) -> bool:
        """Validate alert candle using validator rules."""
        self.next_validation()
        try:
            alert_ok = False
            if alert_idx is not None:
                alert_ok = DojiAnchorSignalCandleValidator.validate_alert_candle(
                    self.lookback_window_df,
                    alert_idx,
                    doji_idx,
                    trend,
                    self.settings.alert_candle_close_to_extreme_threshold,
                    self.settings.alert_candle_max_volume_ratio,
                    self.settings.min_alert_body_size,
                    avg_mom_vol,
                )
            if not alert_ok:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Alert candle validation failed at index {alert_idx}, trend={trend}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    approach=self.APPROACH_NAME
                )
                return False
            self.validations.append(Validation(
                name=nameof(self.settings.alert_candle_close_to_extreme_threshold),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Alert candle validation passed at {alert_idx}",
                status=ValidationStatus.PASSED
            ))
            return True
        except Exception as e:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Alert candle validation failed - {str(e)}",
                log_level=LogLevel.ERROR,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return False

