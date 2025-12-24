# src/stockreports/alert/approach/PRICE_GAP/executor.py

import pandas as pd
import logging
import json
from typing import Optional

# --- Standard Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators

# --- Custom Approach Imports ---
from .settings import PriceGapSettings

class PriceGapExecutor(Executor):
    APPROACH_NAME = Approach.PRICE_GAP
    # Class-level variable to track the last alert timestamp across all instances
    LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = PriceGapSettings(symbol)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the PRICE_GAP approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_price_gap_alerts(df, new_candle_count)
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

    def _find_price_gap_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        """
        Finds alerts based on the price gap pattern.
        """
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        # Determine required lookback
        lookback_period = self.settings.lookback_period if self.settings.use_breakout_confirmation else 1
        required_lookback = lookback_period + 1 # Need at least one previous candle for gap calculation

        df = prepare_indicators(df)
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        # Ensure index is set to 'time' and is timezone-aware
        if 'time' in df.columns:
            df = df.set_index('time')
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            if df.index.tz is None:
                try:
                    from src.stockreports.utils.time_utils import TIMEZONE
                    df.index = df.index.tz_localize(TIMEZONE)
                except Exception:
                    df.index = df.index.tz_localize('UTC')
        df_indexed = df

        # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
        # 1. Define loop_end (most recent index to scan)
        #    We do NOT subtract the forward window here because the signal candle itself
        #    can be the confirmation candle. We want to check the most recent candles too.
        loop_end = len(df_indexed) - 1
        
        # 2. Define min_scan_index (absolute minimum index required for lookback)
        min_scan_index = required_lookback - 1
        
        # 3. Define loop_start (oldest index to scan) based on mode
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In DEPLOYMENT, we scan back enough to cover signals that might be confirmed
            # by the new candles (within the forward window).
            forward_window = self.settings.confirmation_forward_window
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - forward_window + 1)

        for i in range(loop_end, loop_start - 1, -1):
            # Cooldown check
            current_time = df_indexed.index[i]
            if PriceGapExecutor.LATEST_ALERT_TIMESTAMP is not None:
                time_diff = (current_time - PriceGapExecutor.LATEST_ALERT_TIMESTAMP).total_seconds() / 60
                if time_diff < self.settings.cooldown_window:
                    continue

            alert = self._analyze_candle(df_indexed, i)
            
            if alert:
                alerts.append(alert)
                PriceGapExecutor.LATEST_ALERT_TIMESTAMP = current_time
                # Optimization: In deployment, we only need the most recent alert.
                if not is_development_mode:
                    return alerts

        # In DEVELOPMENT mode, return all found alerts in chronological order.
        return alerts[::-1]

    def _analyze_candle(self, df_indexed: pd.DataFrame, i: int) -> Optional[AlertData]:
        """
        Analyzes a single candle for the price gap pattern.
        """
        current_candle = df_indexed.iloc[i]
        prev_candle = df_indexed.iloc[i-1]
        
        # Check for BUY signal
        buy_alert = self._check_buy_signal(df_indexed, i, current_candle, prev_candle)
        if buy_alert:
            return buy_alert
            
        # Check for SELL signal
        sell_alert = self._check_sell_signal(df_indexed, i, current_candle, prev_candle)
        if sell_alert:
            return sell_alert
            
        return None

    def _check_buy_signal(self, df_indexed: pd.DataFrame, i: int, current_candle: pd.Series, prev_candle: pd.Series) -> Optional[AlertData]:
        """
        Checks for a Gap Up (BUY) signal.
        """
        # 1. Check Gap Condition: Open(T) > Close(T-1) + MIN_GAP_SIZE
        gap_size = current_candle['open'] - prev_candle['close']
        
        if gap_size < self.settings.min_gap_size:
            return None
            
        # 2. Optional Breakout Confirmation
        if self.settings.use_breakout_confirmation:
            lookback = self.settings.lookback_period
            window_start_idx = i - lookback
            if window_start_idx < 0:
                return None
                
            window = df_indexed.iloc[window_start_idx : i]
            max_close_in_window = window['close'].max()
            
            if current_candle['close'] <= max_close_in_window:
                self.logger.debug(f"Window ending {current_candle.name}: Failed BUY BREAKOUT_CONFIRMATION. "
                                f"Close {current_candle['close']} <= Max Window Close {max_close_in_window}.")
                return None

        # 3. Forward Window Confirmation
        return self._find_confirmation_in_forward_window(df_indexed, i, gap_size, Signal.BUY, prev_candle)

    def _check_sell_signal(self, df_indexed: pd.DataFrame, i: int, current_candle: pd.Series, prev_candle: pd.Series) -> Optional[AlertData]:
        """
        Checks for a Gap Down (SELL) signal.
        """
        # 1. Check Gap Condition: Close(T-1) > Open(T) + MIN_GAP_SIZE
        gap_size = prev_candle['close'] - current_candle['open']
        
        if gap_size < self.settings.min_gap_size:
            return None
            
        # 2. Optional Breakout Confirmation
        if self.settings.use_breakout_confirmation:
            lookback = self.settings.lookback_period
            window_start_idx = i - lookback
            if window_start_idx < 0:
                return None
                
            window = df_indexed.iloc[window_start_idx : i]
            min_close_in_window = window['close'].min()
            
            if current_candle['close'] >= min_close_in_window:
                self.logger.debug(f"Window ending {current_candle.name}: Failed SELL BREAKOUT_CONFIRMATION. "
                                f"Close {current_candle['close']} >= Min Window Close {min_close_in_window}.")
                return None

        # 3. Forward Window Confirmation
        return self._find_confirmation_in_forward_window(df_indexed, i, gap_size, Signal.SELL, prev_candle)

    def _find_confirmation_in_forward_window(self, df_indexed: pd.DataFrame, signal_idx: int, gap_size: float, signal_type: str, prev_candle: pd.Series) -> Optional[AlertData]:
        """
        Scans the forward window (including the signal candle) for a valid confirmation candle.
        Scans in reverse order (from the end of the window back to the signal candle) to find the latest confirmation.
        """
        forward_window = self.settings.confirmation_forward_window
        min_body_size = self.settings.min_confirmation_body_size
        
        # Get signal candle for comparison
        signal_candle = df_indexed.iloc[signal_idx]

        # Scan from signal_idx up to signal_idx + forward_window - 1
        # Ensure we don't go out of bounds
        end_scan_idx = min(signal_idx + forward_window, len(df_indexed))
        
        # Reverse loop: from end of window back to signal_idx
        for j in range(end_scan_idx - 1, signal_idx - 1, -1):
            candle = df_indexed.iloc[j]
            body_size = abs(candle['close'] - candle['open'])
            
            # Check direction and body size
            is_valid_direction = False
            if signal_type == Signal.BUY:
                is_valid_direction = candle['close'] > candle['open']
            elif signal_type == Signal.SELL:
                is_valid_direction = candle['open'] > candle['close']
            
            # Check progression if not the signal candle
            is_valid_progression = True
            if j > signal_idx:
                if signal_type == Signal.BUY:
                    # Open of alert candle > Open of signal candle
                    if candle['open'] <= signal_candle['open']:
                        is_valid_progression = False
                elif signal_type == Signal.SELL:
                    # Open of alert candle < Open of signal candle (Symmetric logic)
                    if candle['open'] >= signal_candle['open']:
                        is_valid_progression = False

            if is_valid_direction and body_size >= min_body_size and is_valid_progression:
                # Found a valid confirmation candle!
                return self._create_alert(candle, prev_candle, gap_size, signal_type)
                
        return None

    def _create_alert(self, current_candle: pd.Series, prev_candle: pd.Series, gap_size: float, signal_type: str) -> AlertData:
        """
        Creates an alert data instance.
        """
        alert_time = current_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
        
        start_time = prev_candle.name
        if isinstance(start_time, pd.Timestamp):
            start_time = start_time.isoformat()

        details = {
            "gap_size": round(gap_size, 2),
            "min_gap_required": self.settings.min_gap_size,
            "breakout_confirmed": self.settings.use_breakout_confirmation
        }

        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            signal=signal_type,
            alert_time=alert_time,
            alert_price=current_candle['close'],
            approach=self.APPROACH_NAME,
            start_time=start_time,
            start_price=prev_candle['close'],
            magnitude=abs(current_candle['close'] - prev_candle['close']),
            details=json.dumps(details)
        )
