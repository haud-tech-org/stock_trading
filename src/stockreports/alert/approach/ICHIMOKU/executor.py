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
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode

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

    # Chikou Span (Lagging Span)
    df['chikou'] = df['close'].shift(-chikou_lag)
    
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
    """
    alerts = []
    min_required_len = max(
        config.get('TENKAN_PERIOD', 9),
        config.get('KIJUN_PERIOD', 26),
        config.get('SENKOU_B_PERIOD', 52)
    ) + config.get('CHIKOU_LAG', 26) # Add Chikou lag for accurate length check

    if len(df) < min_required_len:
        logging.warning(f"{Approach.ICHIMOKU}: DataFrame has less than {min_required_len} rows, cannot generate alerts.")
        return alerts

    df = _calculate_ichimoku_indicators(df, config)
    df_indexed = df.set_index('time')
    
    chikou_lag = config.get('CHIKOU_LAG', 26)
    
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    grace_period = 0
    
    # The loop now iterates over the entire dataframe to find all historical alerts.
    # Start index must be high enough to have a valid previous candle and Chikou span.
    start_index = max(1, chikou_lag)
    skip_chikou = config.get("SKIP_CHIKOU_CONFIRMATION", False)
    relax_kumo = config.get("RELAX_KUMO_CONDITION", False)

    for i in range(start_index, len(df_indexed)):
        is_new_alert = not is_development_mode and (i >= len(df_indexed) - (new_candle_count + grace_period))

        candle = df_indexed.iloc[i]
        prev_candle = df_indexed.iloc[i-1]
        signal = None

        # --- Bullish Signal Conditions ---
        tenkan_cross_up_kijun = candle['tenkan_sen'] > candle['kijun_sen'] and prev_candle['tenkan_sen'] <= prev_candle['kijun_sen']
        price_above_kumo = candle['close'] > candle['senkou_a'] and candle['close'] > candle['senkou_b']
        chikou_above_price = candle['chikou'] > df_indexed.iloc[i - chikou_lag]['high']

        # Loosened conditions
        tenkan_up = candle['tenkan_sen'] > candle['kijun_sen']
        price_above_either_kumo = candle['close'] > candle['senkou_a'] or candle['close'] > candle['senkou_b']
        chikou_above_close = candle['chikou'] > df_indexed.iloc[i - chikou_lag]['close']

        # BUY logic
        if (tenkan_cross_up_kijun and (price_above_kumo if not relax_kumo else price_above_either_kumo) and (chikou_above_price if not skip_chikou else True)) \
            or (relax_kumo and tenkan_up and price_above_either_kumo and (chikou_above_close if not skip_chikou else True)):
            signal = "BUY"

        # --- Bearish Signal Conditions ---
        else:
            tenkan_cross_down_kijun = candle['tenkan_sen'] < candle['kijun_sen'] and prev_candle['tenkan_sen'] >= prev_candle['kijun_sen']
            price_below_kumo = candle['close'] < candle['senkou_a'] and candle['close'] < candle['senkou_b']
            chikou_below_price = candle['chikou'] < df_indexed.iloc[i - chikou_lag]['low']

            tenkan_down = candle['tenkan_sen'] < candle['kijun_sen']
            price_below_either_kumo = candle['close'] < candle['senkou_a'] or candle['close'] < candle['senkou_b']
            chikou_below_close = candle['chikou'] < df_indexed.iloc[i - chikou_lag]['close']

            if (tenkan_cross_down_kijun and (price_below_kumo if not relax_kumo else price_below_either_kumo) and (chikou_below_price if not skip_chikou else True)) \
                or (relax_kumo and tenkan_down and price_below_either_kumo and (chikou_below_close if not skip_chikou else True)):
                signal = "SELL"

        # --- Common Alert Creation Logic ---
        if signal:
            use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
            use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)

            volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df) and is_volume_spike_confirmed(df, i))

            confirmation_window_df = df.iloc[max(0, i - config.get("CONFIRMATION_WINDOW", 3)):i+1]
            volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_window_df)

            if volume_spike_is_confirmed and volume_is_increasing:
                alert_data = _create_alert(df.iloc[i], df.iloc[i-1], signal, config)
                if alert_data and (is_development_mode or is_new_alert):
                    alerts.append(alert_data)
    
    return alerts

def _create_alert(candle: pd.Series, prev_candle: pd.Series, signal: str, config: dict) -> AlertData:
    """
    Creates an alert data instance. This function can be extended or modified
    to include more complex logic for alert creation.
    """
    alert_time = candle.name
    # Ensure alert_time is a pandas Timestamp with timezone info
    if not isinstance(alert_time, pd.Timestamp):
        alert_time = pd.to_datetime(alert_time)
    if alert_time.tzinfo is None:
        # Use market timezone if available, else UTC
        try:
            from src.stockreports.utils.time_utils import TIMEZONE
            alert_time = alert_time.tz_localize(TIMEZONE)
        except Exception:
            alert_time = alert_time.tz_localize('UTC')
    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

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
        start_time=prev_candle.name,
        magnitude=abs(candle['close'] - prev_candle['close']),
        details=json.dumps(details)
    )
    return alert
