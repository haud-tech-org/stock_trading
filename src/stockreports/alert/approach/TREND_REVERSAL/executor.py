import pandas as pd
import logging
import json
from typing import Optional, List
from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, ValidationStatus, LogLevel, Trend, Signal
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from .settings import TrendReversalSettings
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import window_utils, candle_utils


class TrendReversalExecutor(Executor):
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = TrendReversalSettings(symbol)
        approach_name = Approach.TREND_REVERSAL
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

        # Initialize some variables
        self.h_candle: Optional[pd.Series] = None
        self.mx_candle: Optional[pd.Series] = None
        self.l_candle: Optional[pd.Series] = None

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> List[AlertData]:
        window_size = self.settings.lookback_window
        if len(df) < window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {window_size}, have {len(df)}.",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return self.alerts

        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, window_size)
            if self.lookback_window_df is None:
                continue

            # Pre-requisite data: Find H (highest close), Mx (highest volume), L (lowest close)
            self.h_candle = self._step_find_h_candle()
            if self.h_candle is None:
                continue
            self.mx_candle = self._step_find_mx_candle()
            if self.mx_candle is None:
                continue
            self.l_candle = self._step_find_l_candle()
            if self.l_candle is None:
                continue

            # Main Step 1: Original trend window and pre-trend validations
            self.next_step()
            orig_trend_window, pfx_mn_candle, window_size_val, trend = self._step_trend_window_and_pre_validations()
            if orig_trend_window is None:
                continue

            # Main Step 2: Post-trend validations and reversal window
            self.next_step()
            reversal_trend = candle_utils.get_reversal_trend(trend)
            reversal_window, pst_mn_candle = self._step_post_trend_and_reversal_window(
                mx_candle=self.mx_candle,
                trend=reversal_trend
            )
            if reversal_window is None:
                continue

            # Main Step 3: Final confirmation/validation
            self.next_step()
            if not self._step_final_confirmation_and_alert(
                reversal_window=reversal_window,
                trend=trend
            ):
                continue

            # Step 4: Cooldown Check
            self.next_step()
            signal = candle_utils.get_signal_from_trend(trend)
            if not self._step_cooldown_check(
                last_alert=TrendReversalExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.lookback_window
            ):
                continue

            # Step 5: Details for Alert
            details_alert_dict = self._add_details_for_alert(
                h_candle=self.h_candle,
                mx_candle=self.mx_candle,
                l_candle=self.l_candle,
                orig_trend_window=orig_trend_window,
                pfx_mn_candle=pfx_mn_candle,
                window_size_val=window_size_val,
                trend=trend,
                reversal_window=reversal_window,
                pst_mn_candle=pst_mn_candle
            )

            # Step 6: Alert Creation
            self.next_step()
            alert_data = self._create_alert_with_details(
                    final_signal=signal,
                    final_trend=trend,
                    details=details_alert_dict,
                    final_alert_candle=reversal_window.iloc[-1],
                    final_magnitude=window_size_val
                )
                

            if alert_data is not None:
                self.alerts.append(alert_data)
                TrendReversalExecutor.LATEST_ALERT = alert_data
            else:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    step=self.current_step,
                    message="Alert creation returned None. Alert not appended.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )

            if not self.is_development_mode and len(self.alerts) >= 1:
                return self.alerts

            

        return self.alerts

    def _step_find_h_candle(self) -> Optional[pd.Series]:
        if self.lookback_window_df is not None:
            return self.lookback_window_df.loc[self.lookback_window_df['close'].idxmax()]
        return None

    def _step_find_mx_candle(self) -> Optional[pd.Series]:
        if self.lookback_window_df is not None:
            return candle_utils.find_max_volume_candle(self.lookback_window_df)
        return None

    def _step_find_l_candle(self) -> Optional[pd.Series]:
        if self.lookback_window_df is not None:
            return self.lookback_window_df.loc[self.lookback_window_df['close'].idxmin()]
        return None

    def _step_trend_window_and_pre_validations(
            self,
        ) -> tuple[Optional[pd.DataFrame], Optional[pd.Series], Optional[float], Optional[Trend]]:
        # Validation: orig_start_idx < mx_candle.name
        orig_start_idx = min(self.h_candle.name, self.l_candle.name)
        orig_end_idx = max(self.h_candle.name, self.l_candle.name)
        orig_trend_window = self.lookback_window_df.loc[orig_start_idx:orig_end_idx]
        pfx_mn_candle = candle_utils.find_min_volume_candle(orig_trend_window)
        window_size_val, trend = window_utils.get_window_size_and_trend(orig_trend_window)

        self.next_validation()
        if not orig_end_idx <= self.mx_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"orig_start_idx ({orig_start_idx}) is not before mx_candle (idx={self.mx_candle.name}).",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None, None, None
        else:
            self.validations.append(Validation(
                name="orig_start_idx_before_mx_candle",
                step=self.current_step,
                validation=self.validation_step,
                message="orig_start_idx is before mx_candle.",
                status=ValidationStatus.PASSED
            ))

        # Validation: pfx_mn_candle index < mx_candle index
        self.next_validation()
        if not pfx_mn_candle.name < self.mx_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"pfx_mn_candle (idx={pfx_mn_candle.name}) is not before mx_candle (idx={self.mx_candle.name}).",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None, None, None
        else:
            self.validations.append(Validation(
                name="pfx_mn_candle_before_mx_candle",
                step=self.current_step,
                validation=self.validation_step,
                message="pfx_mn_candle is before mx_candle.",
                status=ValidationStatus.PASSED
            ))

        # Validation: Mx's volume >= pfx_Mn's volume * MIN_PRE_VOLUME_MULTIPLIER
        self.next_validation()
        valid_pre, ratio_pre = candle_utils.validate_volume_ratio(self.mx_candle, pfx_mn_candle, self.settings.min_pre_volume_multiplier)
        if not valid_pre:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Mx volume {self.mx_candle['volume']} < pfx_Mn volume {pfx_mn_candle['volume']} * min_pre_volume_multiplier {self.settings.min_pre_volume_multiplier}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None, None, None
        else:
            self.validations.append(Validation(
                name=nameof(self.settings.min_pre_volume_multiplier),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Pre-trend volume validation passed. Ratio: {ratio_pre:.2f}",
                status=ValidationStatus.PASSED
            ))

        # Validation: window size >= MIN_TREND_MAGNITUDE
        self.next_validation()
        if window_size_val < self.settings.min_trend_magnitude:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window size {window_size_val} < min_trend_magnitude {self.settings.min_trend_magnitude}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None, None, None
        else:
            self.validations.append(Validation(
                name=nameof(self.settings.min_trend_magnitude),
                step=self.current_step,
                validation=self.validation_step,
                message="Trend magnitude validation passed.",
                status=ValidationStatus.PASSED
            ))
        return orig_trend_window, pfx_mn_candle, window_size_val, trend

    def _step_post_trend_and_reversal_window(
        self,
        mx_candle: pd.Series,
        trend: Trend
    ) -> tuple[Optional[pd.DataFrame], Optional[pd.Series]]:
        mx_pos = self.lookback_window_df.index.get_loc(mx_candle.name)
        reversal_window = self.lookback_window_df.iloc[mx_pos:]
        if reversal_window.empty:
            return None, None

        # Build same-trend window based on expected_trend
        if trend == Trend.UPTREND:
            same_trend_window = reversal_window[reversal_window['close'] > reversal_window['open']]
        elif trend == Trend.DOWNTREND:
            same_trend_window = reversal_window[reversal_window['close'] < reversal_window['open']]
        else:
            same_trend_window = reversal_window
        
        # 2. Volume >= previous candle's volume * MIN_ADJACENT_VOLUME_MULTIPLIER
        self.next_validation()
        if len(same_trend_window) < 2:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Reversal window has less than 2 candles.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None

        pst_mn_candle = candle_utils.find_min_volume_candle(same_trend_window)

        # Validation: Mx's volume >= pst_Mn's volume * MIN_POST_VOLUME_MULTIPLIER
        self.next_validation()
        valid_post, ratio_post = candle_utils.validate_volume_ratio(mx_candle, pst_mn_candle, self.settings.min_post_volume_multiplier)
        if not valid_post:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Mx volume {mx_candle['volume']} < pst_Mn volume {pst_mn_candle['volume']} * min_post_volume_multiplier {self.settings.min_post_volume_multiplier}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None
        else:
            self.validations.append(Validation(
                name=nameof(self.settings.min_post_volume_multiplier),
                step=self.current_step,
                validation=self.validation_step,
                message=f"Post-trend volume validation passed. Ratio: {ratio_post:.2f}",
                status=ValidationStatus.PASSED
            ))
        self.next_validation()
        anchor_candle = same_trend_window.iloc[-1]
        anchor_candle_minus_1 = same_trend_window.iloc[-2]
        valid_adj, ratio_adj = candle_utils.validate_volume_ratio(anchor_candle, anchor_candle_minus_1, self.settings.min_adjacent_volume_multiplier)
        if not valid_adj:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Anchor candle volume {anchor_candle['volume']} < previous candle volume {anchor_candle_minus_1['volume']} * min_adjacent_volume_multiplier {self.settings.min_adjacent_volume_multiplier}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None
        else:
            self.validations.append(Validation(
                name="adjacent_volume_validation",
                step=self.current_step,
                validation=self.validation_step,
                message=f"Adjacent volume validation passed. Ratio: {ratio_adj:.2f}",
                status=ValidationStatus.PASSED
            ))

        return reversal_window, pst_mn_candle

    def _step_final_confirmation_and_alert(
        self,
        reversal_window: pd.DataFrame,
        trend: Trend
    ) -> bool:
        potential_alert = reversal_window.iloc[-1]

    # 1. OPEN validation in reversal window based on trend
    # self.next_validation()
    # if trend == Trend.UPTREND:
    #     validated_close_price = reversal_window['open'].max()
    #     val_name = "highest_open_in_reversal_window"
    #     fail_msg = "Potential alert does not have the highest OPEN in reversal window."
    #     pass_msg = "Potential alert has the highest OPEN in reversal window."
    # elif trend == Trend.DOWNTREND:
    #     validated_close_price = reversal_window['open'].min()
    #     val_name = "lowest_open_in_reversal_window"
    #     fail_msg = "Potential alert does not have the lowest OPEN in reversal window."
    #     pass_msg = "Potential alert has the lowest OPEN in reversal window."
    # else:
    #     validated_close_price = None
    #     val_name = "open_in_reversal_window"
    #     fail_msg = "Unknown trend for open validation."
    #     pass_msg = ""

    # if validated_close_price is None or potential_alert['open'] != validated_close_price:
    #     log(
    #         logger=self.logger,
    #         status=ValidationStatus.FAILED,
    #         name=self.__class__.__name__,
    #         alert_time=self.current_window_end_time,
    #         step=self.current_step,
    #         validation=self.validation_step,
    #         message=fail_msg,
    #         log_level=LogLevel.DEBUG,
    #         execution_symbol=self.symbol,
    #         start_time=self.current_window_start_time,
    #         end_time=self.current_window_end_time
    #     )
    #     return False
    # else:
    #     self.validations.append(Validation(
    #         name=val_name,
    #         step=self.current_step,
    #         validation=self.validation_step,
    #         message=pass_msg,
    #         status=ValidationStatus.PASSED
    #     ))

        # 2. Validate l_candle['close'] < potential_alert['close'] < h_candle['close']
        self.next_validation()
        if not (self.l_candle is not None and self.h_candle is not None and self.l_candle['close'] < potential_alert['close'] < self.h_candle['close']):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"potential_alert['close'] ({potential_alert['close']}) is not between l_candle['close'] ({self.l_candle['close']}) and h_candle['close'] ({self.h_candle['close']})",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return False
        else:
            self.validations.append(Validation(
                name="close_between_l_and_h_candle",
                step=self.current_step,
                validation=self.validation_step,
                message=f"potential_alert['close'] is between l_candle['close'] and h_candle['close'].",
                status=ValidationStatus.PASSED
            ))

        # All validations passed
        return True
