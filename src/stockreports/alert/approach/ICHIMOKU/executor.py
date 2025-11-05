# src/stockreports/alert/approach/ICHIMOKU/executor.py
import pandas as pd
import logging
import json

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators, 
    check_advanced_confirmation, 
    can_apply_advanced_confirmation
)
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.regime import prepare_regime_indicators, is_regime_favorable, has_divergence

logger = logging.getLogger(__name__)

def _calculate_ichimoku_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Calculates all necessary Ichimoku indicators."""
    tenkan_period = config.get('TENKAN_PERIOD', 9)
    kijun_period = config.get('KIJUN_PERIOD', 26)
    senkou_b_period = config.get('SENKOU_B_PERIOD', 52)
    chikou_lag = config.get('CHIKOU_LAG', 26)

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
    df['chikou'] = df['close'].shift(chikou_lag)
    
    return df

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the Ichimoku approach. It identifies strong Ichimoku signals
    based on multiple conditions including Kumo, Chikou, and Kijun-sen distance.
    """
    approach_name = Approach.ICHIMOKU
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        if config.get("USE_MARKET_REGIME_FILTER", False):
            df = prepare_regime_indicators(df, config)

        alerts_data = _find_ichimoku_alerts(df, config, new_candle_count)
        logging.info(f"'{approach_name}' approach found {len(alerts_data)} alerts.")

        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

        return AlertResult(
            approach_name=approach_name,
            alerts=alerts_df
        )
    except Exception as e:
        logging.error(f"An error occurred during '{approach_name}' execution: {e}", exc_info=True)
        return AlertResult(
            approach_name=approach_name,
            alerts=pd.DataFrame(),
            status="FAILED",
            message=str(e)
        )

def _find_ichimoku_alerts(df: pd.DataFrame, config: dict, new_candle_count: int) -> list[AlertData]:
    """
    Internal function to find alerts based on Ichimoku signals.
    This function uses a truly unified reverse loop for both deployment and development modes.
    The loop's scan depth is naturally handled by the value of `new_candle_count`.
    """
    alerts = []
    
    df = _calculate_ichimoku_indicators(df, config)
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
    
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    # Determine the minimum amount of data needed for one calculation
    required_lookback = max(
        config.get('TENKAN_PERIOD', 9),
        config.get('KIJUN_PERIOD', 26),
        config.get('SENKOU_B_PERIOD', 52),
        config.get('CHIKOU_LAG', 26)
    )
    
    # Config for the loop
    min_bars_between_alerts = config.get('MIN_BARS_BETWEEN_ALERTS', 5)
    use_regime_filter = config.get("USE_MARKET_REGIME_FILTER", False)
    use_divergence_filter = config.get("USE_DIVERGENCE_FILTER", False)
    use_confirmation_filter = config.get("USE_CONFIRMATION_CANDLE_FILTER", False)
    confirmation_candles = config.get("CONFIRMATION_CANDLE_COUNT", 1)

    # State tracking for signal and alert spacing
    last_alert_idx = float('inf')  # Use infinity for reverse loop

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    end_offset = confirmation_candles if use_confirmation_filter else 0
    loop_end = len(df_indexed) - 1 - end_offset
    loop_start = required_lookback -1

    # The loop's scan depth is naturally optimized by this calculation.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    for i in range(loop_end, loop_start, -1):
        # Stop searching if we are past the active region for the current mode.
        if i < active_region_start:
            break

        # Cooldown check: Ensure enough bars have passed since the last alert found
        if i >= last_alert_idx - min_bars_between_alerts:
            continue

        candle = df_indexed.iloc[i]
        prev_candle = df_indexed.iloc[i-1]
        signal = None

        # --- Bullish Signal Conditions ---
        tenkan_cross_up_kijun = candle['tenkan_sen'] > candle['kijun_sen'] and prev_candle['tenkan_sen'] <= prev_candle['kijun_sen']
        price_above_kumo = candle['close'] > candle['senkou_a'] and candle['close'] > candle['senkou_b']
        chikou_above_price = candle['chikou'] > candle['high']

        if tenkan_cross_up_kijun and price_above_kumo and (chikou_above_price if not config.get("SKIP_CHIKOU_CONFIRMATION", False) else True):
            signal = "BUY"

        # --- Bearish Signal Conditions ---
        else:
            tenkan_cross_down_kijun = candle['tenkan_sen'] < candle['kijun_sen'] and prev_candle['tenkan_sen'] >= prev_candle['kijun_sen']
            price_below_kumo = candle['close'] < candle['senkou_a'] and candle['close'] < candle['senkou_b']
            chikou_below_price = candle['chikou'] < candle['low']

            if tenkan_cross_down_kijun and price_below_kumo and (chikou_below_price if not config.get("SKIP_CHIKOU_CONFIRMATION", False) else True):
                signal = "SELL"

        # --- Common Alert Creation Logic ---
        if signal:
            if use_regime_filter and not is_regime_favorable(candle, signal, config):
                continue

            if use_divergence_filter and has_divergence(df, i, signal, config):
                continue

            # --- Look-forward Confirmation Candle Logic ---
            if use_confirmation_filter:
                is_confirmed = True
                for j in range(1, confirmation_candles + 1):
                    confirmation_candle = df_indexed.iloc[i + j]
                    if (signal == 'BUY' and confirmation_candle['close'] <= candle['close']) or \
                       (signal == 'SELL' and confirmation_candle['close'] >= candle['close']):
                        is_confirmed = False
                        break
                if not is_confirmed:
                    continue

            # Volume Confirmation
            use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
            use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
            use_last_candle_max_volume = config.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)

            volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df) and is_volume_spike_confirmed(df, i))
            
            # The window for volume checks should be consistent. Here, we'll use the confirmation candle and the signal candle.
            volume_check_window = df.iloc[i-1:i+1]
            volume_is_increasing = not use_increasing_volume or is_volume_increasing(volume_check_window)
            last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(volume_check_window)

            if volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed:
                alert_data = _create_alert(df.iloc[i], df.iloc[i-1], signal, config)
                if alert_data:
                    alerts.append(alert_data)
                    last_alert_idx = i
                    
                    # In DEPLOYMENT mode, exit after finding the first valid alert.
                    if not is_development_mode:
                        return alerts

    # In DEVELOPMENT mode, return all found alerts in chronological order.
    return alerts[::-1]

def _create_alert(candle: pd.Series, prev_candle: pd.Series, signal: str, config: dict) -> AlertData:
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
        "price_kumo_relation": "Above" if signal == "BUY" else "Below",
        "chikou_confirmation": "Yes"
    }

    alert = AlertData(
        approach=Approach.ICHIMOKU,
        id=alert_id,
        signal=signal,
        alert_price=candle['close'],
        alert_time=alert_time,
        start_price=prev_candle['close'],
        start_time=start_time,
        magnitude=abs(candle['close'] - prev_candle['close']),
        details=json.dumps(details),
        profit_loss=None,
        period_time=None,
        status=None,
        validation_price_time=None,
        time_to_best_price=None,
        min_expected_profit_loss=None,
        symbol=None
    )
    return alert
