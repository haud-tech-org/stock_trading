import pandas as pd
import logging
import json
from typing import List, Optional, Tuple

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import ComparisonSettings
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.utils.historical_data_manager import get_historical_data

class ComparisonExecutor(Executor):
    APPROACH_NAME = Approach.COMPARISON
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = ComparisonSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        # This approach should only run for its configured primary symbol.
        if self.symbol != self.settings.primary_symbol:
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame())

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

    def _find_comparison_alerts(self, df_primary: pd.DataFrame, new_candle_count: int) -> List[AlertData]:
        # --- Data Loading for Reference Symbol ---
        start_time = df_primary['time'].min()
        end_time = df_primary['time'].max()
        df_reference = get_historical_data(self.settings.reference_symbol, start_time=start_time, end_time=end_time)

        if df_reference is None or df_reference.empty:
            self.logger.warning(f"Reference dataframe for {self.settings.reference_symbol} is empty. Skipping alert finding.")
            return []

        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        window_size = self.settings.lookback_window

        # Align dataframes
        df_merged = pd.merge(df_primary, df_reference, left_index=True, right_index=True, suffixes=('_primary', '_reference'))
        if len(df_merged) < window_size:
            self.logger.warning(f"Not enough aligned data for {self.APPROACH_NAME}: requires {window_size}, have {len(df_merged)}.")
            return alerts

        df_indexed = df_merged.reset_index()

        loop_end_index = len(df_indexed) - 1
        min_scan_index = window_size - 1

        if is_development_mode:
            loop_start_index = min_scan_index
        else:
            loop_start_index = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end_index, loop_start_index - 1, -1):
            window_df = df_indexed.iloc[i - window_size + 1 : i + 1]

            anchor_idx, potential_signal = self._find_crossover_point(window_df)
            if anchor_idx is None:
                continue

            alert_candle = window_df.iloc[-1]
            anchor_candle = window_df.loc[anchor_idx]

            # 1. Divergence Check
            divergence = alert_candle['close_primary'] - alert_candle['close_reference']

            # 2. Trend Consistency and Magnitude Check
            primary_trend_magnitude = alert_candle['close_primary'] - anchor_candle['close_primary']
            reference_trend_magnitude = alert_candle['close_reference'] - anchor_candle['close_reference']

            is_consistent_trend = (primary_trend_magnitude > 0 and reference_trend_magnitude > 0) or \
                                  (primary_trend_magnitude < 0 and reference_trend_magnitude < 0)

            if not is_consistent_trend:
                continue

            if abs(primary_trend_magnitude) > self.settings.max_primary_trend_magnitude:
                continue
            
            # Determine the final signal based on trend direction and potential signal from crossover
            final_signal = None
            if primary_trend_magnitude > 0 and potential_signal == Signal.BUY and not self.settings.disable_buy_signal:
                final_signal = Signal.BUY
            elif primary_trend_magnitude < 0 and potential_signal == Signal.SELL and not self.settings.disable_sell_signal:
                final_signal = Signal.SELL

            if final_signal is None:
                continue

            # 3. Divergence Threshold and Consistency Check
            if not (
                (final_signal == Signal.BUY and divergence >= self.settings.min_divergence_threshold) or
                (final_signal == Signal.SELL and divergence <= -self.settings.min_divergence_threshold)
            ):
                continue

            # 4. Cooldown Check
            if is_in_cooldown(
                new_alert_time=alert_candle['time'],
                new_signal=final_signal,
                latest_alert=ComparisonExecutor.LATEST_ALERT,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            alert_data = self._create_alert_data(alert_candle, anchor_candle, final_signal, divergence)
            alerts.append(alert_data)
            ComparisonExecutor.LATEST_ALERT = alert_data

            if not is_development_mode:
                return alerts
        
        return alerts

    def _find_crossover_point(self, window_df: pd.DataFrame) -> Tuple[Optional[int], Optional[Signal]]:
        """
        Finds the most recent crossover point and the potential signal it implies.
        Searches backwards and returns the index and signal of the first flip found.
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
                return window_df.index[i], potential_signal

        return None, None

    def _create_alert_data(self, alert_candle: pd.Series, anchor_candle: pd.Series, signal: Signal, divergence: float) -> AlertData:
        alert_time = alert_candle['time']
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
        magnitude = abs(alert_candle['close_primary'] - anchor_candle['close_primary'])

        details = {
            "reference_symbol": self.settings.reference_symbol,
            "divergence_at_alert": divergence,
            "anchor_candle_time": anchor_candle['time'].isoformat(),
            "anchor_candle_price_primary": anchor_candle['close_primary'],
            "anchor_candle_price_reference": anchor_candle['close_reference'],
        }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=alert_candle['close_primary'],
            alert_time=alert_time,
            start_price=anchor_candle['close_primary'],
            start_time=anchor_candle['time'].isoformat(),
            magnitude=magnitude,
            details=json.dumps(details)
        )
