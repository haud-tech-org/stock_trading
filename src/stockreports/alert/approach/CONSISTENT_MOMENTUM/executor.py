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

        # --- Alert Confirmation and Generation ---
        final_candle = current_candle
        is_breakout_confirmed = False
        original_signal = signal

        # If breakout confirmation is enabled, run it as the last validation step.
        if self.settings.use_breakout_confirmation:
            confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
            
            # This function now returns a tuple: (candle, confirmed_signal)
            confirmation_result = self._confirm_breakout_in_forward_window(df_indexed, confirmation_candle_index, signal)
            
            if confirmation_result is None:
                return None  # Breakout not confirmed, so no alert.

            # Unpack the results
            confirmed_candle, confirmed_signal = confirmation_result
            
            if confirmed_candle is None:
                 return None # Should not happen if result is not None, but as a safeguard.

            # If breakout is confirmed, update the final candle and mark as confirmed.
            # Also, update the signal, as it might have been flipped by the reversal logic.
            final_candle = confirmed_candle
            signal = confirmed_signal
            is_breakout_confirmed = True
        
        # Now that the final_candle is determined, generate the details.
        details = {
            "momentum_start_price": start_candle['open'],
            "momentum_start_time": to_iso8601_with_tz(start_candle.name),
            "momentum_window_size": window_size,
        }
        if is_breakout_confirmed:
            details["reason"] = "Consistent Momentum with Breakout"
            if signal != original_signal:
                details["reason"] = "Consistent Momentum with Reversal"
            details["breakout_lookback_minutes"] = self.settings.peak_bottom_lookback_period
        else:
            details["reason"] = "Consistent Momentum"

        # Create the AlertData object with the final, confirmed data.
        alert_id = str(int(final_candle.name.tz_convert('UTC').timestamp()))
        current_price = final_candle['close']
        momentum_start_price = start_candle['open']

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            alert_time=final_candle.name,
            signal=signal,
            alert_price=current_price,
            start_price=momentum_start_price,
            start_time=start_candle.name,
            magnitude=round(abs(current_price - momentum_start_price), 2),
            details=json.dumps(details)
        )

    def _confirm_breakout_in_forward_window(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> Optional[tuple[pd.Series, Signal]]:
        """
        Confirms a breakout by checking if any candle in the emerging window (back + forward) breaks the most recent peak/trough.
        Returns a tuple of (confirmation_candle, confirmed_signal) if confirmed, otherwise None.
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
            return df_indexed.iloc[alert_candle_index], signal # No history, consider confirmed at alert candle

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
            self.logger.debug(f"[{alert_candle_time}] No peak/trough found in lookback; confirming at alert candle.")
            return df_indexed.iloc[alert_candle_index], signal # No peak/trough, consider confirmed at alert candle

        self.logger.debug(f"[{alert_candle_time}] Breakout price set to {breakout_price:.2f} for {signal} signal.")

        # 3. Check the forward window for a breakout, including the alert candle itself.
        forward_window_size = self.settings.breakout_forward_window
        body_to_range_min_ratio = self.settings.body_to_range_min_ratio

        # The forward window starts AT the alert candle index.
        start_index = alert_candle_index
        end_index = min(alert_candle_index + forward_window_size, len(df_indexed))
        
        if start_index >= end_index:
            self.logger.debug(f"[{alert_candle_time}] Forward window is empty, cannot confirm breakout.")
            return None

        forward_window = df_indexed.iloc[start_index:end_index]
        self.logger.debug(f"[{alert_candle_time}] Checking forward window from {forward_window.index[0]} to {forward_window.index[-1]} for breakout.")

        # Helper to check direction
        def is_same_direction(candle, sig):
            if sig == Signal.BUY:
                return candle['close'] > candle['open']
            else:
                return candle['close'] < candle['open']

        # --- Scenario 1: Check the alert candle itself for "Big Body" confirmation ---
        alert_candle = forward_window.iloc[0]
        candle_time = alert_candle.name
        self.logger.debug(f"[{candle_time}] Checking Scenario 1: 'Big Body' on the alert candle itself.")

        candle_range = alert_candle['high'] - alert_candle['low']
        if candle_range > 0:
            candle_body = abs(alert_candle['close'] - alert_candle['open'])
            body_ratio = candle_body / candle_range

            is_body_big = body_ratio >= body_to_range_min_ratio
            is_dir_correct = is_same_direction(alert_candle, signal)
            
            price_breaks_out = False
            if signal == Signal.BUY and alert_candle['close'] > breakout_price:
                price_breaks_out = True
            elif signal == Signal.SELL and alert_candle['close'] < breakout_price:
                price_breaks_out = True

            if is_body_big and is_dir_correct and price_breaks_out:
                self.logger.debug(f"[{candle_time}] Confirmed by 'Big Body' rule on the alert candle.")
                return alert_candle, signal
            else:
                self.logger.debug(f"[{candle_time}] 'Big Body' rule failed on the alert candle.")

        # --- Scenario 2: Advanced Reversal and Breakout Logic ---
        if len(forward_window) >= 3:
            self.logger.debug(f"[{alert_candle_time}] Checking Scenario 2: Advanced Reversal and Breakout.")

            # --- New Reversal Logic (Scenario 2.A) ---
            self.logger.debug(f"[{alert_candle_time}] Checking new reversal logic.")
            
            # 1. Find key candles
            candle_mx = forward_window.loc[forward_window['volume'].idxmax()]
            candle_mn = forward_window.loc[forward_window['volume'].idxmin()]
            mn_index_in_fw = forward_window.index.get_loc(candle_mn.name)

            # 2. Find candle_n (candle after min volume candle)
            if mn_index_in_fw < len(forward_window) - 1:
                candle_n = forward_window.iloc[mn_index_in_fw + 1]
                self.logger.debug(f"[{alert_candle_time}] Found Mn candle at {candle_mn.name} and N candle at {candle_n.name}.")

                # Ensure N and Mn are different candles before proceeding
                if candle_n.name == candle_mn.name:
                    self.logger.debug(f"[{alert_candle_time}] Candle N and Mn are the same, skipping reversal check.")
                    return None # Or continue to the next part of the logic if that's desired

                # 3. Define price-action lookback window (up to 5 candles before N)
                price_lookback_end_index = mn_index_in_fw + 1 # Index of N
                price_lookback_start_index = max(0, price_lookback_end_index - 5)
                price_action_window = forward_window.iloc[price_lookback_start_index:price_lookback_end_index]

                if not price_action_window.empty:
                    # 4. Find peak/trough prices in the lookback window
                    peak_trough_open_price = None
                    peak_trough_close_price = None
                    if signal == Signal.BUY: # Look for SELL reversal (peak)
                        peak_trough_open_price = price_action_window['open'].max()
                        peak_trough_close_price = price_action_window['close'].max()
                    else: # Look for BUY reversal (trough)
                        peak_trough_open_price = price_action_window['open'].min()
                        peak_trough_close_price = price_action_window['close'].min()
                    
                    # 5. Apply reversal conditions
                    reversal_multiplier = self.settings.reversal_volume_multiplier
                    volume_condition_met = candle_mx['volume'] >= candle_mn['volume'] * reversal_multiplier

                    if volume_condition_met:
                        self.logger.debug(f"[{candle_n.name}] Reversal volume condition met.")
                        
                        # New average body price check, where candle_mn is candle_n_minus_1 by definition
                        avg_price_n = (candle_n['open'] + candle_n['close']) / 2
                        avg_price_n_minus_1 = (candle_mn['open'] + candle_mn['close']) / 2
                        
                        price_condition_met = False
                        reversal_trend_met = False

                        if signal == Signal.SELL: # Original SELL, check for BUY reversal
                            price_condition_met = candle_n['close'] > peak_trough_close_price and candle_n['open'] > peak_trough_open_price
                            reversal_trend_met = avg_price_n > avg_price_n_minus_1
                            if price_condition_met and reversal_trend_met:
                                confirmed_signal = Signal.BUY
                        
                        elif signal == Signal.BUY: # Original BUY, check for SELL reversal
                            price_condition_met = candle_n['close'] < peak_trough_close_price and candle_n['open'] < peak_trough_open_price
                            reversal_trend_met = avg_price_n < avg_price_n_minus_1
                            if price_condition_met and reversal_trend_met:
                                confirmed_signal = Signal.SELL

                        if price_condition_met and reversal_trend_met:
                            self.logger.info(f"[{candle_n.name}] Confirmed reversal from {signal} to {confirmed_signal} based on new logic.")
                            return candle_n, confirmed_signal
                        else:
                            self.logger.debug(f"[{candle_n.name}] Reversal price or trend condition failed.")
                    else:
                        self.logger.debug(f"[{candle_n.name}] Reversal volume condition failed.")
            else:
                self.logger.debug(f"[{alert_candle_time}] Min volume candle is the last in window, cannot check for reversal.")


            # --- Breakout Volume Check (Scenario 2.B) ---
            # This part now acts as a fallback if the new reversal logic doesn't trigger.
            candle_j = forward_window.iloc[-1]
            candle_j_minus_1 = forward_window.iloc[-2]
            candle_j_minus_2 = forward_window.iloc[-3]
            candle_time = candle_j.name

            volume_multiplier = self.settings.breakout_volume_multiplier
            volume_condition = (candle_j['volume'] >= candle_j_minus_1['volume'] * volume_multiplier and
                                candle_j['volume'] >= candle_j_minus_2['volume'] * volume_multiplier)

            if signal == Signal.BUY:
                price_condition = (candle_j['close'] > breakout_price and
                                   candle_j_minus_1['close'] > breakout_price and
                                   candle_j_minus_2['close'] > breakout_price)
                # The latest candle's close must be the highest of the three.
                trend_condition = candle_j['close'] > candle_j_minus_1['close'] and candle_j['close'] > candle_j_minus_2['close']

                if price_condition and trend_condition and volume_condition:
                    self.logger.debug(f"[{candle_time}] Confirmed by 'Consistent Price Action' on the 3 latest candles.")
                    return candle_j, signal
                else:
                    self.logger.debug(f"[{candle_time}] 'Consistent Price Action' (BUY) failed on the 3 latest candles.")

            elif signal == Signal.SELL:
                price_condition = (candle_j['close'] < breakout_price and
                                   candle_j_minus_1['close'] < breakout_price and
                                   candle_j_minus_2['close'] < breakout_price)
                # The latest candle's close must be the lowest of the three.
                trend_condition = candle_j['close'] < candle_j_minus_1['close'] and candle_j['close'] < candle_j_minus_2['close']

                if price_condition and trend_condition and volume_condition:
                    self.logger.debug(f"[{candle_time}] Confirmed by 'Consistent Price Action' on the 3 latest candles.")
                    return candle_j, signal
                else:
                    self.logger.debug(f"[{candle_time}] 'Consistent Price Action' (SELL) failed on the 3 latest candles.")

        # If neither scenario confirms the breakout, return None.
        self.logger.debug(f"[{alert_candle_time}] No breakout confirmation found from the specific scenarios.")
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

        # The main loop can now run up to the last candle. The forward window logic
        # inside the confirmation function will handle boundaries.
        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In DEPLOYMENT, we must scan back far enough to catch momentum windows
            # that could be confirmed by one of the new candles.
            forward_window = self.settings.breakout_forward_window if self.settings.use_breakout_confirmation else 0
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - forward_window)

        for i in range(loop_end, loop_start - 1, -1):
            # Ensure we don't look past the end of the dataframe for the momentum window.
            if i < window_size - 1:
                continue

            window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()

            alert = self._analyze_window(window, df_indexed, window_size)

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
