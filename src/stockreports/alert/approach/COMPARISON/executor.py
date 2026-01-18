import pandas as pd
import logging
import json
from typing import List, Optional, Tuple

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import ComparisonSettings
from src.stockreports.alert.common.confirmation.reversal import validate_reversal_confirmation
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.alert.common.signal.market_trend_validation import validate_concurrent_trend
from src.stockreports.alert.common.signal.trend_utils import validate_trend
from src.stockreports.utils.historical_data_manager import get_historical_data
from src.stockreports.utils.log_factory import log

class ComparisonExecutor(Executor):
    APPROACH_NAME = Approach.COMPARISON
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = ComparisonSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        # This approach should only run for its configured primary symbol.
        if self.symbol != self.settings.primary_symbol:
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Skipping run for symbol '{self.symbol}' because it does not match the configured primary symbol '{self.settings.primary_symbol}'.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol
            )
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame())

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

            alerts_data = self._find_comparison_alerts(df, new_candle_count)
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
            self.logger.error(f"[{self.__class__.__name__}] An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=pd.DataFrame(),
                status="FAILED",
                message=str(e)
            )

    def _find_comparison_alerts(self, df_primary: pd.DataFrame, new_candle_count: int = 0) -> List[AlertData]:
        # --- Data Loading for Reference Symbol ---
        start_time = df_primary['time'].min()
        end_time = df_primary['time'].max()
        df_reference = get_historical_data(
            symbol=self.settings.reference_symbol, 
            start_time=start_time, 
            end_time=end_time
        )

        if df_reference is None or df_reference.empty:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Reference dataframe for {self.settings.reference_symbol} is empty. Skipping alert finding.",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol
            )
            return []

        # Reset index to ensure we are working with integer-based indices
        df_primary = df_primary.reset_index()
        df_reference = df_reference.reset_index()

        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        window_size = self.settings.lookback_window

        # Align dataframes by merging on the 'time' column
        df_merged = pd.merge(df_primary, df_reference, on='time', suffixes=('_primary', '_reference'))
        if len(df_merged) < window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough aligned data for {self.APPROACH_NAME}: requires {window_size}, have {len(df_merged)}.",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol
            )
            return alerts

        df_indexed = df_merged

        loop_end_index = len(df_indexed) - 1
        min_scan_index = window_size - 1

        if is_development_mode:
            loop_start_index = min_scan_index
        else:
            loop_start_index = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end_index, loop_start_index - 1, -1):
            window_df = df_indexed.iloc[i - window_size + 1 : i + 1]
            self.current_window_end_time = window_df.iloc[-1]['time']
            self.current_window_start_time = window_df.iloc[0]['time']
            self.current_step = 1

            # Step 1: Find the crossover point using the merged data
            anchor_pos, potential_signal = self._find_crossover_point(window_df=window_df)
            if anchor_pos is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="No crossover point found in window.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Get the timestamp of the anchor event from its position in the window
            anchor_timestamp = window_df.iloc[anchor_pos]['time']

            # Step 2: Validate reversal on the reference symbol's data
            self.current_step += 1
            ref_confirmation_df = df_reference[df_reference['time'] >= anchor_timestamp]
            if len(ref_confirmation_df) < 2:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Not enough data for reversal validation on reference symbol.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            validation_result = validate_reversal_confirmation(
                confirmation_df=ref_confirmation_df,
                reversal_signal=potential_signal,
                min_alert_body_size=self.settings.min_alert_body_size,
                max_distance_close_price=self.settings.max_distance_close_price,
                min_volume_multiplier=self.settings.volume_multiplier
            )

            if validation_result is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Reversal validation failed on reference symbol.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            
            ref_alert_candle, ref_anchor_candle = validation_result
            
            # --- Consolidated Primary Candle Lookups ---
            # Find the alert candle on the primary dataframe.
            alert_candle_primary_series = df_primary[df_primary['time'] == ref_alert_candle['time']]
            if alert_candle_primary_series.empty:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Could not find the primary alert candle at {ref_alert_candle['time']}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            alert_candle_primary = alert_candle_primary_series.iloc[0]

            # Find the anchor candle on the primary dataframe.
            anchor_candle_primary_series = df_primary[df_primary['time'] == anchor_timestamp]
            if anchor_candle_primary_series.empty:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Could not find the primary anchor candle at {anchor_timestamp}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue
            anchor_candle_primary = anchor_candle_primary_series.iloc[0]
            # --- End Lookups ---

            # Step 3: Volume Profile Validation on Primary Symbol
            self.current_step += 1
            # Define the volume window from the crossover anchor to the end of the lookback window.
            volume_window_end_time = window_df.iloc[-1]['time']
            volume_window_df = df_primary[
                (df_primary['time'] >= anchor_timestamp) &
                (df_primary['time'] <= volume_window_end_time)
            ]

            if len(volume_window_df) < 2:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Not enough data in volume window for analysis.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Find the candles with minimum and maximum volume in this window.
            min_vol_candle = volume_window_df.loc[volume_window_df['volume'].idxmin()]
            max_vol_candle = volume_window_df.loc[volume_window_df['volume'].idxmax()]

            # Validation 1: Min volume must occur before max volume.
            if not (min_vol_candle['time'] < max_vol_candle['time']):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=1,
                    message=f"Minimum volume at {min_vol_candle['time']} did not occur before maximum volume at {max_vol_candle['time']}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation 2: The volume of the max candle must be significantly larger than the min candle.
            if not (max_vol_candle['volume'] >= min_vol_candle['volume'] * self.settings.volume_multiplier):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=2,
                    message=f"Max volume ({max_vol_candle['volume']}) is not >= {self.settings.volume_multiplier}x the min volume ({min_vol_candle['volume']}).",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation 3: The final alert candle must occur at or after the max volume candle.
            if not (ref_alert_candle['time'] >= max_vol_candle['time']):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=3,
                    message=f"Alert candle at {ref_alert_candle['time']} occurred before the maximum volume candle at {max_vol_candle['time']}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Validation 4: The alert candle's volume must be >= its preceding candle's volume.
            alert_candle_index = alert_candle_primary.name
            if alert_candle_index > 0:
                alert_candle_minus_1 = df_primary.iloc[alert_candle_index - 1]
                if alert_candle_primary['volume'] < alert_candle_minus_1['volume']:
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=4,
                        message=f"Alert candle volume ({alert_candle_primary['volume']}) was less than previous candle volume ({alert_candle_minus_1['volume']}).",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue

            # Step 4: Check the primary trend's magnitude (cheap check first)
            self.current_step += 1
            primary_trend_magnitude = alert_candle_primary['close'] - anchor_candle_primary['close']

            failed_magnitude_check = False
            reason = ""
            if potential_signal == Signal.BUY:
                if not (self.settings.min_primary_trend_magnitude <= primary_trend_magnitude <= self.settings.max_primary_trend_magnitude):
                    failed_magnitude_check = True
                    reason = f"magnitude ({primary_trend_magnitude:.2f}) was not within [{self.settings.min_primary_trend_magnitude}, {self.settings.max_primary_trend_magnitude}]"
            elif potential_signal == Signal.SELL:
                min_sell_magnitude = -self.settings.max_primary_trend_magnitude
                max_sell_magnitude = -self.settings.min_primary_trend_magnitude
                if not (min_sell_magnitude <= primary_trend_magnitude <= max_sell_magnitude):
                    failed_magnitude_check = True
                    reason = f"magnitude ({primary_trend_magnitude:.2f}) was not within [{min_sell_magnitude}, {max_sell_magnitude}]"
            
            if failed_magnitude_check:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Primary trend for {potential_signal} signal failed because {reason}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Step 5: Define confirmation window and validate trends
            self.current_step += 1
            # The window is from the candle AFTER the anchor reversal up to the alert candle
            confirmation_window_primary = df_primary[
                (df_primary['time'] > ref_alert_candle['time']) & 
                (df_primary['time'] <= self.current_window_end_time)
            ]
            confirmation_window_ref = df_reference[
                (df_reference['time'] > ref_alert_candle['time']) & 
                (df_reference['time'] <= self.current_window_end_time)
            ]

            if confirmation_window_primary.empty or confirmation_window_ref.empty:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Confirmation window is empty.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            primary_trend_signal = validate_trend(
                df=confirmation_window_primary,
                use_monotonic_check=True
            )
            ref_trend_signal = validate_trend(
                df=confirmation_window_ref,
                use_monotonic_check=True
            )

            # Step 6: Determine the final signal based on trend agreement
            final_signal = None
            if (potential_signal == Signal.BUY and 
                primary_trend_signal == Signal.BUY and 
                ref_trend_signal == Signal.BUY and 
                not self.settings.disable_buy_signal):
                final_signal = Signal.BUY
            elif (potential_signal == Signal.SELL and 
                  primary_trend_signal == Signal.SELL and 
                  ref_trend_signal == Signal.SELL and 
                  not self.settings.disable_sell_signal):
                final_signal = Signal.SELL

            if final_signal is None:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Trend signals did not agree. Potential: {potential_signal}, Primary: {primary_trend_signal}, Reference: {ref_trend_signal}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # Step 7: Validate against overall market trend (optional)
            self.current_step += 1
            if self.settings.enable_market_trend_validation:
                if not validate_concurrent_trend(
                    expected_signal=final_signal,
                    alert_time=ref_alert_candle['time'],
                    min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                    require_all=False
                ):
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        message="Concurrent market trend validation failed.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time
                    )
                    continue

            # Step 8: Cooldown Logic
            self.current_step += 1
            if is_in_cooldown(
                new_alert_time=alert_candle_primary['time'],
                new_signal=final_signal,
                latest_alert=ComparisonExecutor.LATEST_ALERT,
                cooldown_window=self.settings.cooldown_window
            ):
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message=f"Alert for {final_signal} is in cooldown.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )
                continue

            # If all validations pass, create the alert
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="All validation steps passed. Creating alert.",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            alert_data = self._create_alert_data(
                signal=final_signal,
                primary_alert_candle=alert_candle_primary,
                ref_alert_candle=ref_alert_candle,
                primary_anchor_candle=anchor_candle_primary,
                ref_anchor_candle=ref_anchor_candle
            )
            alerts.append(alert_data)
            ComparisonExecutor.LATEST_ALERT = alert_data
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message=f"Comparison alert generated for {alert_candle_primary['time']}.",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )

            # If not in development mode, stop after the first alert
            if not is_development_mode:
                return alerts
        
        return alerts

    def _find_crossover_point(self, window_df: pd.DataFrame) -> Tuple[Optional[int], Optional[Signal]]:
        """
        Finds the most recent crossover point and the potential signal it implies.
        Searches backwards and returns the relative position and signal of the first flip found.
        """
        if len(window_df) < 2:
            return None, None

        # Iterate backwards from the end of the window.
        for i in range(len(window_df) - 1, 0, -1):
            current_candle = window_df.iloc[i]
            prev_candle = window_df.iloc[i - 1]

            prev_primary_below_ref = prev_candle['close_primary'] < prev_candle['close_reference']
            curr_primary_below_ref = current_candle['close_primary'] < current_candle['close_reference']

            if prev_primary_below_ref != curr_primary_below_ref:
                # Crossover detected. Determine the signal based on the direction of the cross.
                potential_signal = Signal.BUY if not curr_primary_below_ref else Signal.SELL
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    alert_time=current_candle['time'],
                    step=self.current_step,
                    message=f"Crossover found at {current_candle['time']}: Prev Primary < Ref: {prev_primary_below_ref}, Curr Primary < Ref: {curr_primary_below_ref}. Signal: {potential_signal}",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol
                )
                return i, potential_signal
            else:
                # Log why a crossover did not happen for these two candles
                relation = "below" if curr_primary_below_ref else "above"
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    alert_time=current_candle['time'],
                    step=self.current_step,
                    message=(
                        f"No crossover at {current_candle['time']}: Primary remained {relation} reference. "
                        f"Prev: {prev_candle['close_primary']:.2f} vs {prev_candle['close_reference']:.2f}, "
                        f"Curr: {current_candle['close_primary']:.2f} vs {current_candle['close_reference']:.2f}"
                    ),
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol
                )

        return None, None

    def _create_alert_data(self, signal: Signal, primary_alert_candle: pd.Series, ref_alert_candle: pd.Series, primary_anchor_candle: pd.Series, ref_anchor_candle: pd.Series) -> AlertData:
        alert_time = primary_alert_candle['time']
        alert_id = str(int(alert_time.timestamp()))
        magnitude = abs(primary_alert_candle['close'] - primary_anchor_candle['close'])
        details = {
            "primary_symbol": self.settings.primary_symbol,
            "reference_symbol": self.settings.reference_symbol,
            "primary_alert_price": primary_alert_candle['close'],
            "ref_alert_price": ref_alert_candle['close'],
            "primary_anchor_price": primary_anchor_candle['close'],
            "ref_anchor_price": ref_anchor_candle['close'],
            "primary_anchor_time": primary_anchor_candle['time'].isoformat(),
            "ref_anchor_time": ref_anchor_candle['time'].isoformat(),
        }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=primary_alert_candle['close'],
            alert_time=alert_time,
            start_price=primary_anchor_candle['close'],
            start_time=primary_anchor_candle['time'].isoformat(),
            magnitude=magnitude,
            details=json.dumps(details)
        )
