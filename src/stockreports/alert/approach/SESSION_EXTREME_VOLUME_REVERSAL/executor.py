
import pandas as pd
import logging
from typing import Optional, List
from varname import nameof
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation, ValidationStatus
from src.stockreports.alert.common.constants import Approach, Trend
from src.stockreports.utils import log_factory
from src.stockreports.utils import candle_utils
from src.stockreports.utils.log_factory import log
from src.stockreports.alert.common.constants import LogLevel
from .settings import SessionExtremeVolumeReversalSettings

class SessionExtremeVolumeReversalExecutor(Executor):
    """
    Executor for the SESSION_EXTREME_VOLUME_REVERSAL approach.
    Identifies alert candles that are session extremes in close and volume, with config-driven validation.
    """
    LATEST_ACCEPTED_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = SessionExtremeVolumeReversalSettings(symbol)
        approach_name = Approach.SESSION_EXTREME_VOLUME_REVERSAL
        super().__init__(symbol, approach_name, self.settings)
        
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> List[AlertData]:
        """
        Implements the abstract method from the base class. Finds all SESSION_EXTREME_VOLUME_REVERSAL alerts in the given DataFrame.
        Mirrors the structure and patterns of VOLUME_REVERSAL/executor.py.
        """
        window_size_max_price = self.settings.lookback_window      

        if len(df) < window_size_max_price:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {window_volume_size}, have {len(df)}.",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol
            )
            return self.alerts
        
        # Pre-calculate the lookback window from 09:30:00 to current
        session_start_idx = df[df['time'].dt.time >= pd.to_datetime('09:30:00').time()].index.min()
        if pd.isna(session_start_idx):
            log_factory.log(
                self.logger,
                f"No session start found for 09:30:00",
                0, 0, ValidationStatus.FAILED, self.symbol
            )
            return self.alerts
        lookback_volume_df = df.loc[session_start_idx:]
        window_volume_size = len(lookback_volume_df)
        if window_volume_size < 1:
            log_factory.log(
                self.logger,
                f"Session window is empty after 09:30:00.",
                0, 0, ValidationStatus.FAILED, self.symbol
            )
            return self.alerts

        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=window_size_max_price
        )

        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, window_size_max_price)
            if self.lookback_window_df is None:
                continue


            # Step 1: Session window is already the lookback_window_df
            session_window = self.lookback_window_df

            # Step 2: Find alert candidate (last candle in window)
            alert_candle = session_window.iloc[-1]

            # Step 3: Trend validation (close is session extreme)
            self.next_step()
            trend_validation_result = self._step_trend_extreme_validation(session_window)
            if trend_validation_result is None:
                continue
            _, trend = trend_validation_result

            # Step 4: Volume max validation
            self.next_step()
            if not self._step_max_volume_validation(session_window):
                continue

            # Step 5: Volume threshold validation
            self.next_step()
            if not self._step_min_volume_multiplier_validation(lookback_volume_df, alert_candle):
                continue

            reversal_trend = candle_utils.get_reversal_trend(trend)
            reversal_signal = candle_utils.get_signal_from_trend(reversal_trend)
            
            # Step 6: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=SessionExtremeVolumeReversalExecutor.LATEST_ACCEPTED_ALERT,
                signal=reversal_signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Step 7: Create details for alert
            details_dict = self._add_details_for_alert(
                window=session_window,
                alert_candle=alert_candle
            )

            # Step 8: Alert creation
            self.next_step()
            alert = self._create_alert_with_details(
                final_signal=reversal_signal,  # Set to the appropriate signal if available
                final_trend=reversal_trend,   # Set to the appropriate trend if available
                final_alert_candle=alert_candle,
                final_magnitude=self.settings.magnitude_threshold,  # Set to the appropriate magnitude if available
                details=details_dict
            )
            if alert is not None:
                self.alerts.append(alert)
                SessionExtremeVolumeReversalExecutor.LATEST_ACCEPTED_ALERT = alert

            if not self.is_development_mode and len(self.alerts) >= 1:
                return self.alerts

        return self.alerts[::-1]

    def _step_trend_extreme_validation(self, window: pd.DataFrame) -> Optional[tuple[bool, Trend]]:
        """
        Validates that the last candle in the window is the session's close extreme in the trend direction.
        Uses candle_utils.get_trend_from_candle for trend determination.
        Validation is by index: the alert candle's index must match the index of the max/min close in the window.
        Mirrors the formatting and validation patterns of VOLUME_REVERSAL/executor.py.
        """
        self.next_validation()
        alert_candle = window.iloc[-1]
        trend = candle_utils.get_trend_from_candle(alert_candle)
        closes = window['close']
        alert_idx = window.index[-1]
        if trend == Trend.UPTREND:
            max_idx = closes.idxmax()
            valid = alert_idx == max_idx
            fail_msg = f"Alert candle index {alert_idx} is not the max close index ({max_idx}) in session window."
            pass_msg = f"Alert candle index {alert_idx} is the max close index in session window."
        elif trend == Trend.DOWNTREND:
            min_idx = closes.idxmin()
            valid = alert_idx == min_idx
            fail_msg = f"Alert candle index {alert_idx} is not the min close index ({min_idx}) in session window."
            pass_msg = f"Alert candle index {alert_idx} is the min close index in session window."
        else:
            # Unknown trend, return None for Optional[tuple[bool, Trend]]
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Unknown trend for session window.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        if not valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=fail_msg,
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
        else:
            self.validations.append(Validation(
                name=nameof(self._step_trend_extreme_validation),
                step=self.current_step,
                validation=self.validation_step,
                message=pass_msg,
                status=ValidationStatus.PASSED
            ))
            return True, trend

    def _step_max_volume_validation(self, window: pd.DataFrame) -> bool:
        """
        Validates that the alert candle is the max volume candle in the session window (by index).
        """
        self.next_validation()
        max_vol_idx = window['volume'].idxmax()
        alert_idx = window.index[-1]
        is_max = alert_idx == max_vol_idx
        if not is_max:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Alert candle index {alert_idx} is not the max volume index ({max_vol_idx}) in session window.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return False
        else:
            self.validations.append(Validation(
                name=nameof(self._step_max_volume_validation),
                step=self.current_step,
                validation=self.validation_step,
                message="Alert candle is the max volume candle in session window.",
                status=ValidationStatus.PASSED
            ))
            return True

    def _step_min_volume_multiplier_validation(self, window: pd.DataFrame, alert_candle: pd.Series) -> bool:
        """
        Validates that the alert candle's volume is at least the average session volume times the min_volume_multiplier.
        Compares alert candle's volume to the average volume of the window.
        """
        self.next_validation()
        avg_vol = window['volume'].mean()
        threshold = avg_vol * self.settings.min_volume_multiplier
        alert_idx = window.index[-1]
        alert_vol = alert_candle['volume']
        is_valid = alert_vol >= threshold
        ratio = alert_vol / avg_vol if avg_vol > 0 else 0
        if not is_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=(f"Volume multiplier check failed: alert_idx={alert_idx}, alert_vol={alert_vol}, avg_vol={avg_vol:.2f}, multiplier={self.settings.min_volume_multiplier}, threshold={threshold:.2f}, ratio={ratio:.2f}"),
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return False
        self.validations.append(Validation(
            name=nameof(self.settings.min_volume_multiplier),
            step=self.current_step,
            validation=self.validation_step,
            message=(f"Volume multiplier check passed: alert_idx={alert_idx}, alert_vol={alert_vol}, avg_vol={avg_vol:.2f}, multiplier={self.settings.min_volume_multiplier}, threshold={threshold:.2f}, ratio={ratio:.2f}"),
            status=ValidationStatus.PASSED
        ))
        return True

    # Use the base class's _create_alert_with_details; do not redefine it here.
