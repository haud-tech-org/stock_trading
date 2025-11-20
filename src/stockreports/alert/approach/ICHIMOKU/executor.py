# src/stockreports/alert/approach/ICHIMOKU/executor.py
import pandas as pd
import logging
import json
from typing import Optional

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    _is_rsi_not_exhausted,
    is_signal_confirmed
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.regime import has_divergence


class IchimokuExecutor(Executor):
    APPROACH_NAME = Approach.ICHIMOKU

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = loader.get_settings()
        self.signal_settings = loader.get_signal_settings()
        self.logger = logging.getLogger(__name__)
        self.CONFIG = self.signal_settings.APPROACH_CONFIG.get(
            self.APPROACH_NAME, self.signal_settings.APPROACH_CONFIG.get("default", {})
        )

    def _calculate_ichimoku_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates all necessary Ichimoku indicators."""
        tenkan_period = self.CONFIG.get('TENKAN_PERIOD', 9)
        kijun_period = self.CONFIG.get('KIJUN_PERIOD', 26)
        senkou_b_period = self.CONFIG.get('SENKOU_B_PERIOD', 52)
        chikou_lag = self.CONFIG.get('CHIKOU_LAG', 26)

        # Tenkan-sen (Conversion Line)
        high_tenkan = df['high'].rolling(window=tenkan_period).max()
        low_tenkan = df['low'].rolling(window=tenkan_period).min()
        df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

        # Kijun-sen (Base Line)
        high_kijun = df['high'].rolling(window=kijun_period).max()
        low_kijun = df['low'].rolling(window=kijun_period).min()
        df['kijun_sen'] = (high_kijun + low_kijun) / 2

        # Senkou Span A (Leading Span A)
        df['senkou_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(kijun_period)

        # Senkou Span B (Leading Span B)
        high_senkou_b = df['high'].rolling(window=senkou_b_period).max()
        low_senkou_b = df['low'].rolling(window=senkou_b_period).min()
        df['senkou_b'] = ((high_senkou_b + low_senkou_b) / 2).shift(kijun_period)

        # Chikou Span (Lagging Span) - Current close shifted back
        df['chikou'] = df['close'].shift(-chikou_lag)
        
        return df

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the Ichimoku approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_ichimoku_alerts(df, new_candle_count)
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

    def _find_ichimoku_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        """
        Internal function to find alerts based on Ichimoku signals.
        """
        alerts = []
        
        df = self._calculate_ichimoku_indicators(df)

        # Determine the minimum amount of data needed for one calculation
        required_lookback = max(
            self.CONFIG.get('TENKAN_PERIOD', 9),
            self.CONFIG.get('KIJUN_PERIOD', 26),
            self.CONFIG.get('SENKOU_B_PERIOD', 52),
            self.CONFIG.get('CHIKOU_LAG', 26)
        )

        # All indicators must be prepared first.
        df = prepare_indicators(df)
        
        can_run_analysis = can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback)
        if not can_run_analysis:
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
        
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        # Config for the loop
        min_bars_between_alerts = self.CONFIG.get('MIN_BARS_BETWEEN_ALERTS', 5)
        use_divergence_filter = self.CONFIG.get("USE_DIVERGENCE_FILTER", False)
        use_confirmation_filter = self.CONFIG.get("USE_CONFIRMATION_CANDLE_FILTER", False)
        confirmation_candles = self.CONFIG.get("CONFIRMATION_CANDLE_COUNT", 1)

        # State tracking for signal and alert spacing
        last_alert_idx = float('inf')  # Use infinity for reverse loop

        # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
        end_offset = confirmation_candles if use_confirmation_filter else 0
        loop_end = len(df_indexed) - 1 - end_offset
        loop_start = required_lookback -1

        # The loop's scan depth is naturally optimized by this calculation.
        active_region_start = len(df_indexed) - new_candle_count - required_lookback

        for i in range(loop_end, loop_start - 1, -1):
            if i < active_region_start:
                break # Stop searching if we are past the active region for the current mode.

            alert = self._analyze_candle(df_indexed, i, use_divergence_filter, use_confirmation_filter, confirmation_candles)
            
            if alert:
                # --- Volume Confirmation ---
                volume_spike_is_confirmed = not self.CONFIG.get("USE_VOLUME_CONFIRMATION", False) or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), i))
                
                if not volume_spike_is_confirmed:
                    continue

                alerts.append(alert)

        # In DEVELOPMENT mode, return all found alerts in chronological order.
        return alerts[::-1]

    def _analyze_candle(self, df_indexed, i, use_divergence_filter, use_confirmation_filter, confirmation_candles):
        candle = df_indexed.iloc[i]
        prev_candle = df_indexed.iloc[i-1]
        signal: Optional[Signal] = None

        # --- Bullish Signal Conditions ---
        tenkan_cross_up_kijun = candle['tenkan_sen'] > candle['kijun_sen'] and prev_candle['tenkan_sen'] <= prev_candle['kijun_sen']
        price_above_kumo = candle['close'] > candle['senkou_a'] and candle['close'] > candle['senkou_b']
        
        # Ensure the index for chikou lookup is valid
        chikou_lookup_idx = i - self.CONFIG.get('CHIKOU_LAG', 26)
        if chikou_lookup_idx < 0:
            return None
        chikou_above_price = candle['chikou'] > df_indexed['high'].iloc[chikou_lookup_idx]

        if tenkan_cross_up_kijun and price_above_kumo and (chikou_above_price if not self.CONFIG.get("SKIP_CHIKOU_CONFIRMATION", False) else True):
            signal = Signal.BUY

        # --- Bearish Signal Conditions ---
        else:
            tenkan_cross_down_kijun = candle['tenkan_sen'] < candle['kijun_sen'] and prev_candle['tenkan_sen'] >= prev_candle['kijun_sen']
            price_below_kumo = candle['close'] < candle['senkou_a'] and candle['close'] < candle['senkou_b']
            
            # Ensure the index for chikou lookup is valid
            chikou_lookup_idx = i - self.CONFIG.get('CHIKOU_LAG', 26)
            if chikou_lookup_idx < 0:
                return None
            chikou_below_price = candle['chikou'] < df_indexed['low'].iloc[chikou_lookup_idx]

            if tenkan_cross_down_kijun and price_below_kumo and (chikou_below_price if not self.CONFIG.get("SKIP_CHIKOU_CONFIRMATION", False) else True):
                signal = Signal.SELL

        # --- Common Alert Creation Logic ---
        if signal:
            # --- Indicator Confirmation ---
            # Step 1: Check for RSI exhaustion on the signal candle.
            # For Ichimoku, we only check the signal candle itself.
            candles_for_exhaustion_check = [candle]
            if not _is_rsi_not_exhausted(candles_for_exhaustion_check, signal, self.CONFIG):
                return None

            # Step 2: Check for confirmation on the signal candle.
            if not is_signal_confirmed(candle, signal, self.CONFIG):
                return None

            if use_divergence_filter and has_divergence(df_indexed, i, signal, self.CONFIG):
                return None

            # --- Look-forward Confirmation Candle Logic ---
            if use_confirmation_filter:
                is_confirmed = True
                for j in range(1, confirmation_candles + 1):
                    confirmation_candle = df_indexed.iloc[i + j]
                    if (signal == Signal.BUY and confirmation_candle['close'] <= candle['close']) or \
                       (signal == Signal.SELL and confirmation_candle['close'] >= candle['close']):
                        is_confirmed = False
                        break
                if not is_confirmed:
                    return None

            return self._create_alert(candle, prev_candle, signal)

    def _create_alert(self, candle: pd.Series, prev_candle: pd.Series, signal: Signal) -> AlertData:
        """
        Creates an alert data instance. This function can be extended or modified
        to include more complex logic for alert creation.
        """
        # Use the same logic as CONSECUTIVE_POWER_CANDLES for id, alert_time, start_time, suggested_price
        # Ensure alert_time is a pandas Timestamp with timezone info
        # Robustly get alert_time from index or fallback to 'time' column or now
        alert_time = candle.name
        if pd.isnull(alert_time) or not isinstance(alert_time, pd.Timestamp):
            alert_time = candle.get('time', pd.Timestamp.utcnow())
            if not isinstance(alert_time, pd.Timestamp):
                alert_time = pd.to_datetime(alert_time)
        if alert_time.tzinfo is None:
            try:
                from src.stockreports.utils.time_utils import TIMEZONE
                alert_time = alert_time.tz_localize(TIMEZONE)
            except Exception:
                alert_time = alert_time.tz_localize('UTC')
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        # start_time: use previous candle's name, ensure it's a timestamp and format as ISO string with timezone (like alert_time)
        start_time = prev_candle.name
        if pd.isnull(start_time) or not isinstance(start_time, pd.Timestamp):
            start_time = prev_candle.get('time', pd.Timestamp.utcnow())
            if not isinstance(start_time, pd.Timestamp):
                start_time = pd.to_datetime(start_time)
        if start_time.tzinfo is None:
            try:
                from src.stockreports.utils.time_utils import TIMEZONE
                start_time = start_time.tz_localize(TIMEZONE)
            except Exception:
                start_time = start_time.tz_localize('UTC')
        # Format as ISO string with timezone, matching alert_time
        start_time = start_time.isoformat()

        details = {
            "tenkan_sen": round(candle['tenkan_sen'], 2),
            "kijun_sen": round(candle['kijun_sen'], 2),
            "price_kumo_relation": "Above" if signal == Signal.BUY else "Below",
            "chikou_confirmation": "Yes"
        }

        alert = AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=candle['close'],
            alert_time=alert_time,
            start_price=prev_candle['close'],
            start_time=start_time,
            magnitude=abs(candle['close'] - prev_candle['close']),
            details=json.dumps(details)
        )
        return alert
