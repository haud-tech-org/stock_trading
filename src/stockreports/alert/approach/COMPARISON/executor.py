import pandas as pd
import logging
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData, ConfirmationResult
from .confirmation import ComparisonConfirmation
from .settings import ComparisonSignalSettings
from src.stockreports.utils.data_utils import load_data_for_development, load_live_data
from src.stockreports.utils.historical_data_manager import get_historical_data
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.volume import (
    is_volume_increasing, 
    is_last_candle_volume_max, 
    is_volume_spike_confirmed, 
    can_apply_volume_confirmation
)


class ComparisonExecutor(Executor):
    APPROACH_NAME = Approach.COMPARISON
    LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None

    def __init__(self, symbol: str):
        self.settings = ComparisonSignalSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the COMPARISON approach. It takes a DataFrame and returns an AlertResult.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")

            alerts_data = self._find_comparison_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

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

    def _find_comparison_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        """
        Finds alerts by comparing the main symbol against a reference symbol,
        using a unified reverse loop for both DEPLOYMENT and DEVELOPMENT modes.
        """
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT

        # --- 1. Initial Setup & Config ---
        
        if self.symbol != self.settings.primary_symbol:
            self.logger.warning(f"Executor symbol '{self.symbol}' does not match settings primary symbol '{self.settings.primary_symbol}'. Skipping.")
            return alerts

        if not self.settings.referenced_symbol:
            return alerts

        # --- 2. Data Loading from Cache ---
        start_time = df['time'].min()
        end_time = df['time'].max()
        
        ref_data = get_historical_data(self.settings.referenced_symbol, start_time=start_time, end_time=end_time)

        if ref_data is None or ref_data.empty:
            self.logger.warning(f"Could not retrieve data for reference symbol '{self.settings.referenced_symbol}' for the required time window. Skipping.")
            return alerts

        main_data = df.set_index('time')
        ref_data = ref_data.set_index('time')
        aligned_main, aligned_ref = main_data.align(ref_data, join='inner', axis=0)

        # --- 3. Indicator Calculation ---
        ma_period = self.settings.ma_short_period
        aligned_main[f'ma_{ma_period}'] = aligned_main['close'].rolling(window=ma_period).mean()
        aligned_ref[f'ma_{ma_period}'] = aligned_ref['close'].rolling(window=ma_period).mean()
        
        final_main, final_ref = aligned_main.dropna().align(aligned_ref.dropna(), join='inner', axis=0)

        if final_main.empty or len(final_main) < ma_period:
            self.logger.warning(f"Not enough aligned data to run comparison after indicator calculation. Required: {ma_period}, have: {len(final_main)}.")
            return alerts

        # --- 4. Unified Reverse Loop ---
        confirmation_checker = ComparisonConfirmation(self.settings)
        cooldown_period_minutes = self.settings.cooldown_period  # Use dedicated cooldown setting
        
        loop_end = len(final_main) - 1
        min_scan_index = self.settings.lookback_window - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In production, we only scan the new candles, but never go below the minimum required lookback
            loop_start = max(min_scan_index, len(final_main) - new_candle_count)

        for i in range(loop_end, loop_start - 1, -1):
            current_candle_time = final_main.index[i]

            # Time-based cooldown check using the instance-level timestamp
            if ComparisonExecutor.LATEST_ALERT_TIMESTAMP is not None:
                time_since_last_alert = current_candle_time - ComparisonExecutor.LATEST_ALERT_TIMESTAMP
                if time_since_last_alert.total_seconds() / 60 < cooldown_period_minutes:
                    continue

            main_window = final_main.iloc[:i + 1]
            ref_window = final_ref.iloc[:i + 1]

            data_window = {
                self.symbol: main_window,
                self.settings.referenced_symbol: ref_window
            }

            confirmation_result = confirmation_checker.confirm(data_window)

            if confirmation_result:
                reversal_time = confirmation_result.reversal_time
                
                # --- Volume Confirmation ---
                use_volume_spike = self.settings.use_volume_confirmation
                use_increasing_volume = self.settings.use_increasing_volume_confirmation
                use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

                # Define the window for volume checks, typically the lookback window ending at the current candle
                volume_check_window_df = main_window.iloc[-self.settings.lookback_window:]

                volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(final_main) and is_volume_spike_confirmed(final_main.reset_index(), i))
                volume_is_increasing = not use_increasing_volume or is_volume_increasing(volume_check_window_df)
                last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(volume_check_window_df)

                if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
                    continue
                # --- End Volume Confirmation ---

                alert = self._create_alert(
                    candle=main_window.iloc[-1],
                    alert_info=confirmation_result,
                    reversal_time=reversal_time,
                    reversal_price=main_window.loc[reversal_time]['open'] if reversal_time else main_window.iloc[-1]['open'],
                    referenced_symbol=self.settings.referenced_symbol,
                    settings=self.settings
                )
                alerts.append(alert)
                
                # Update the instance-level timestamp with the new alert's time
                ComparisonExecutor.LATEST_ALERT_TIMESTAMP = alert.alert_time

                if not is_development_mode:
                    return alerts

        return alerts[::-1]

    def _create_alert(self, candle: pd.Series, alert_info: ConfirmationResult, reversal_time: pd.Timestamp, reversal_price: float, referenced_symbol: str, settings: ComparisonSignalSettings) -> AlertData:
        """
        Creates and returns a standardized AlertData object.
        """
        alert_time = candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        # Ensure start_time is a Timestamp object, not None
        start_time = reversal_time if reversal_time is not None else alert_time

        details = {
            "trend": alert_info.trend,
            "referenced_symbol": referenced_symbol,
            "ma_period": settings.ma_short_period,
            "lookback_window": settings.lookback_window,
            "cooldown_period": settings.cooldown_period
        }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=alert_info.signal,
            alert_price=candle['close'],
            alert_time=alert_time,
            start_price=reversal_price,
            start_time=start_time,
            magnitude=abs(candle['close'] - reversal_price),
            details=json.dumps(details)
        )
