import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    is_signal_confirmed,
    _is_rsi_not_exhausted
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.common.volume import (
    is_volume_spike_confirmed, 
    can_apply_volume_confirmation, 
    is_last_candle_volume_max,
    is_volume_increasing
)
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.utils.time_utils import to_iso8601_with_tz
from .settings import ConsistentMomentumSettings


class ConsistentMomentumExecutor(Executor):
    APPROACH_NAME = Approach.CONSISTENT_MOMENTUM
    LATEST_ACCEPTED_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = ConsistentMomentumSettings(symbol)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the CONSISTENT_MOMENTUM approach. It takes a DataFrame and returns an AlertResult.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            df = prepare_indicators(df)

            alerts_data = self._find_consistent_momentum_alerts(df, new_candle_count)
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

    def _analyze_window(self, window: pd.DataFrame, df_indexed: pd.DataFrame, window_size: int) -> Optional[AlertData]:
        """
        Analyzes a single window of data to find a consistent momentum alert.
        """
        is_all_bullish = (window['close'] > window['open']).all()
        is_all_bearish = (window['close'] < window['open']).all()

        if not (is_all_bullish or is_all_bearish):
            return None

        window['avg_price'] = (window['open'] + window['close']) / 2
        
        is_momentum_confirmed = False
        if is_all_bullish:
            is_momentum_confirmed = window['avg_price'].is_monotonic_increasing
            signal = Signal.BUY
        elif is_all_bearish:
            is_momentum_confirmed = window['avg_price'].is_monotonic_decreasing
            signal = Signal.SELL
        
        if not is_momentum_confirmed:
            return None

        current_candle = window.iloc[-1]
        candle_range = (current_candle['high'] - current_candle['low'])
        if candle_range == 0: 
            return None

        # Restore momentum strength check (total body vs total wick)
        window['body'] = abs(window['close'] - window['open'])
        window['range'] = window['high'] - window['low']
        window['wick'] = window['range'] - window['body']

        total_body = window['body'].sum()
        total_wick = window['wick'].sum()

        if total_body <= total_wick:
            return None

        # Restore RSI exhaustion check
        start_candle = window.iloc[0]
        end_candle = window.iloc[-1]
        candles_for_rsi_check = [start_candle, end_candle]

        if not _is_rsi_not_exhausted(candles_for_rsi_check, signal, self.settings):
            return None

        # Restore general signal confirmation (MA, ADX, etc.)
        if not is_signal_confirmed(end_candle, signal, self.settings):
            return None

        # The breakout confirmation logic has been moved to the main loop
        # to allow for forward-window analysis.

        use_volume_spike = self.settings.use_volume_confirmation
        use_increasing_volume = self.settings.use_volume_increasing_confirmation
        use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

        confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
        confirmation_df = df_indexed.iloc[confirmation_candle_index - window_size + 1 : confirmation_candle_index + 1]

        volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), confirmation_candle_index))
        volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)

        if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
            return None

        current_price = current_candle['close']
        momentum_start_price = start_candle['open']
        momentum_start_time_iso = to_iso8601_with_tz(start_candle.name)
        
        alert_id = str(int(current_candle.name.tz_convert('UTC').timestamp()))
        
        details = {
            "reason": "Consistent Momentum",
            "momentum_start_price": momentum_start_price,
            "momentum_start_time": momentum_start_time_iso,
            "momentum_window_size": window_size,
        }

        # Breakout details will be added later if confirmed.

        alert_data = AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            alert_time=current_candle.name,
            signal=signal,
            alert_price=current_price,
            start_price=momentum_start_price,
            start_time=start_candle.name,
            magnitude=round(abs(current_price - momentum_start_price), 2),
            details=json.dumps(details)
        )
        return alert_data

    def _confirm_breakout_in_forward_window(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> Optional[pd.Series]:
        """
        Confirms a breakout by checking if any candle in the emerging window (back + forward) breaks the most recent peak/trough.
        Returns the confirmation candle if confirmed, otherwise None.
        """
        lookback_minutes = self.settings.peak_bottom_lookback_period
        prominence = self.settings.peak_trough_prominence
        alert_candle_time = df_indexed.index[alert_candle_index]

        # 1. Define the lookback period to find the breakout level
        if lookback_minutes is None:
            lookback_df = df_indexed.loc[:alert_candle_time].iloc[:-1]
        else:
            lookback_start_time = alert_candle_time - pd.Timedelta(minutes=lookback_minutes)
            lookback_df = df_indexed.loc[lookback_start_time:alert_candle_time].iloc[:-1]

        if lookback_df.empty:
            return df_indexed.iloc[alert_candle_index] # No history, consider confirmed at alert candle

        # 2. Find the highest peak or lowest trough to set the breakout price
        breakout_price = None
        if signal == Signal.BUY:
            peaks, _ = find_peaks(lookback_df['close'], prominence=prominence)
            if peaks.size > 0:
                breakout_price = lookback_df['close'].iloc[peaks].max()
        elif signal == Signal.SELL:
            troughs, _ = find_peaks(-lookback_df['close'], prominence=prominence)
            if troughs.size > 0:
                breakout_price = lookback_df['close'].iloc[troughs].min()

        if breakout_price is None:
            return df_indexed.iloc[alert_candle_index] # No peak/trough, consider confirmed at alert candle

        # 3. Check the emerging window (back + forward) for a breakout
        forward_window_size = self.settings.breakout_forward_window
        back_window_size = self.settings.window_size
        
        start_index = alert_candle_index - back_window_size + 1
        end_index = min(alert_candle_index + 1 + forward_window_size, len(df_indexed))
        
        emerging_window = df_indexed.iloc[start_index : end_index]
        body_to_range_min_ratio = self.settings.body_to_range_min_ratio

        breakout_candle = None
        breakout_idx_in_window = -1

        # Find Breakout Candle (B)
        for idx, (time, candle) in enumerate(emerging_window.iterrows()):
            candle_range = candle['high'] - candle['low']
            if candle_range == 0:
                continue
            
            candle_body = abs(candle['close'] - candle['open'])
            body_ratio = candle_body / candle_range
            
            if body_ratio < body_to_range_min_ratio:
                continue

            is_breakout = False
            if signal == Signal.BUY and candle['close'] > breakout_price:
                is_breakout = True
            elif signal == Signal.SELL and candle['close'] < breakout_price:
                is_breakout = True
            
            if is_breakout:
                breakout_candle = candle
                breakout_idx_in_window = idx
                break
        
        if breakout_candle is None:
            return None

        # Get absolute index of breakout candle in df_indexed
        # emerging_window starts at start_index
        abs_breakout_index = start_index + breakout_idx_in_window
        
        # Check if B+1 exists
        if abs_breakout_index + 1 >= len(df_indexed):
            return None # Cannot confirm yet

        candle_b = breakout_candle
        candle_b_plus_1 = df_indexed.iloc[abs_breakout_index + 1]

        # Helper to check direction
        def is_same_direction(candle, sig):
            if sig == Signal.BUY:
                return candle['close'] > candle['open']
            else:
                return candle['close'] < candle['open']

        # Attempt Immediate Confirmation (at B+1)
        # Condition: Vol(B+1) > Vol(B) AND Direction(B+1) == Signal
        if candle_b_plus_1['volume'] > candle_b['volume'] and is_same_direction(candle_b_plus_1, signal):
            return candle_b_plus_1

        # Attempt Delayed Confirmation
        # Reference Candle = B+1
        reference_candle = candle_b_plus_1
        
        # Iterate from B+2 onwards, up to end_index
        # We need to map end_index (which was relative to df_indexed) to the loop
        # The loop should go from abs_breakout_index + 2 to end_index
        
        for i in range(abs_breakout_index + 2, end_index):
            candle_c = df_indexed.iloc[i]
            
            # Conditions:
            # 1. Vol(C) > Vol(Reference)
            # 2. Direction(C) == Signal
            # 3. Close(C) > Breakout Price (for BUY) or < Breakout Price (for SELL)
            
            if candle_c['volume'] <= reference_candle['volume']:
                continue

            # Found a candle with higher volume
            dir_condition = is_same_direction(candle_c, signal)
            
            price_condition = False
            if signal == Signal.BUY:
                price_condition = candle_c['close'] > breakout_price
            else:
                price_condition = candle_c['close'] < breakout_price
            
            if dir_condition and price_condition:
                return candle_c
            
            # If volume is higher but other conditions fail, update reference candle
            reference_candle = candle_c

        return None

    def _find_consistent_momentum_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Finds alerts based on a consistent momentum pattern using a unified reverse loop.
        """
        alerts = []
        window_size = self.settings.window_size
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        if window_size < 2:
            self.logger.error(f"{self.APPROACH_NAME}: 'CONFIRMATION_WINDOW' must be at least 2. Aborting.")
            return alerts

        required_lookback = window_size
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        df_indexed = df.set_index('time')

        # Adjust loop end to account for the forward window
        forward_window_size = self.settings.breakout_forward_window if self.settings.use_breakout_confirmation else 0
        loop_end = len(df_indexed) - 1
        
        loop_start = required_lookback - 1
        active_region_start = len(df_indexed) - new_candle_count - required_lookback - forward_window_size

        for i in range(loop_end, loop_start - 1, -1):
            if i < active_region_start:
                break

            window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()
            
            alert = self._analyze_window(window, df_indexed, window_size)
            
            if alert:
                # New breakout confirmation logic using a forward-looking window.
                if self.settings.use_breakout_confirmation:
                    confirmation_candle = self._confirm_breakout_in_forward_window(df_indexed, i, alert.signal)
                    if confirmation_candle is None:
                        alert = None # Invalidate alert if breakout is not confirmed
                    else:
                        # If breakout is confirmed, update the alert details.
                        details = json.loads(alert.details)
                        details["reason"] = "Consistent Momentum with Breakout"
                        details["breakout_lookback_minutes"] = self.settings.peak_bottom_lookback_period
                        alert.details = json.dumps(details)
                        
                        # Update alert time and price to the confirmation candle
                        alert.alert_time = confirmation_candle.name
                        alert.alert_price = confirmation_candle['close']
                        alert.id = str(int(confirmation_candle.name.tz_convert('UTC').timestamp()))

                if alert:
                    # Cooldown Check: Ignore alerts with the same direction within the cooldown period
                    if ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT is not None:
                        time_since_last = alert.alert_time - ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT.alert_time
                        minutes_since_last = time_since_last.total_seconds() / 60
                        
                        if (minutes_since_last < self.settings.cooldown_period and 
                            alert.signal == ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT.signal):
                            alert = None 

                if alert:
                    alerts.append(alert)
                    
                    # Update global state with the accepted alert
                    ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT = alert

                    if not is_development_mode:
                        return alerts

        return alerts[::-1]
