import pandas as pd
import logging
import json
from typing import Optional

from src.stockreports.alert.model.models import AlertResult, AlertData, ConfirmationResult
from .confirmation import ComparisonConfirmation
from .settings import ComparisonSignalSettings
from src.stockreports.utils.data_utils import load_data_for_development, load_live_data
from src.stockreports.utils.historical_data_manager import get_historical_data
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal

settings = loader.get_settings()
logger = logging.getLogger(__name__)

APPROACH_NAME = Approach.COMPARISON
LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None

def run_analysis(df: pd.DataFrame, new_candle_count: int) -> AlertResult:
    """
    Entry point for the COMPARISON approach. It takes a DataFrame and returns an AlertResult.
    """
    try:
        logger.info(f"Running '{APPROACH_NAME}' approach...")
        
        alerts_data = _find_comparison_alerts(df, new_candle_count)
        logger.info(f"'{APPROACH_NAME}' approach found {len(alerts_data)} alerts.")

        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=alerts_df
        )
    except Exception as e:
        logger.error(f"An error occurred during '{APPROACH_NAME}' execution: {e}", exc_info=True)
        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=pd.DataFrame(),
            status="FAILED",
            message=str(e)
        )

def _find_comparison_alerts(df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
    """
    Finds alerts by comparing the main symbol against a reference symbol,
    using a unified reverse loop for both DEPLOYMENT and DEVELOPMENT modes.
    """
    global LATEST_ALERT_TIMESTAMP
    alerts = []
    is_development_mode = settings.MODE == Mode.DEVELOPMENT

    # --- 1. Initial Setup & Config ---
    if 'symbol' not in df.columns:
        df['symbol'] = loader.get_settings().SYMBOLS[0]

    symbol = df['symbol'].iloc[0]
    approach_settings = ComparisonSignalSettings(symbol)
    
    if not approach_settings.referenced_symbol:
        return alerts

    # --- 2. Data Loading from Cache ---
    start_time = df['time'].min()
    end_time = df['time'].max()
    
    ref_data = get_historical_data(approach_settings.referenced_symbol, start_time=start_time, end_time=end_time)

    if ref_data is None or ref_data.empty:
        logger.warning(f"Could not retrieve data for reference symbol '{approach_settings.referenced_symbol}' for the required time window. Skipping.")
        return alerts

    main_data = df.set_index('time')
    ref_data = ref_data.set_index('time')
    aligned_main, aligned_ref = main_data.align(ref_data, join='inner', axis=0)

    # --- 3. Indicator Calculation ---
    ma_period = approach_settings.ma_short_period
    aligned_main[f'ma_{ma_period}'] = aligned_main['close'].rolling(window=ma_period).mean()
    aligned_ref[f'ma_{ma_period}'] = aligned_ref['close'].rolling(window=ma_period).mean()
    
    final_main, final_ref = aligned_main.dropna().align(aligned_ref.dropna(), join='inner', axis=0)

    if final_main.empty or len(final_main) < ma_period:
        logger.warning(f"Not enough aligned data to run comparison after indicator calculation. Required: {ma_period}, have: {len(final_main)}.")
        return alerts

    # --- 4. Unified Reverse Loop ---
    confirmation_checker = ComparisonConfirmation(approach_settings)
    cooldown_period_minutes = approach_settings.cooldown_period  # Use dedicated cooldown setting
    
    loop_end = len(final_main) - 1
    loop_start = ma_period - 1 
    active_region_start = len(final_main) - new_candle_count - ma_period

    for i in range(loop_end, loop_start - 1, -1):
        if not is_development_mode and i < active_region_start:
            break

        current_candle_time = final_main.index[i]

        # Time-based cooldown check using the module-level timestamp
        if LATEST_ALERT_TIMESTAMP is not None:
            time_since_last_alert = current_candle_time - LATEST_ALERT_TIMESTAMP
            if time_since_last_alert.total_seconds() / 60 < cooldown_period_minutes:
                continue

        main_window = final_main.iloc[:i + 1]
        ref_window = final_ref.iloc[:i + 1]

        data_window = {
            symbol: main_window,
            approach_settings.referenced_symbol: ref_window
        }

        confirmation_result = confirmation_checker.confirm(data_window)

        if confirmation_result:
            reversal_time = confirmation_result.reversal_time
            
            alert = _create_alert(
                candle=main_window.iloc[-1],
                alert_info=confirmation_result,
                symbol=symbol,
                reversal_time=reversal_time,
                reversal_price=main_window.loc[reversal_time]['open'] if reversal_time else main_window.iloc[-1]['open'],
                referenced_symbol=approach_settings.referenced_symbol,
                settings=approach_settings
            )
            alerts.append(alert)
            
            # Update the module-level timestamp with the new alert's time
            LATEST_ALERT_TIMESTAMP = alert.alert_time

            if not is_development_mode:
                return alerts

    return alerts[::-1]

def _create_alert(candle: pd.Series, alert_info: ConfirmationResult, symbol: str, reversal_time: pd.Timestamp, reversal_price: float, referenced_symbol: str, settings: ComparisonSignalSettings) -> AlertData:
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
        approach=APPROACH_NAME,
        id=alert_id,
        symbol=symbol,
        signal=alert_info.signal,
        alert_price=candle['close'],
        alert_time=alert_time,
        start_price=reversal_price,
        start_time=start_time,
        magnitude=abs(candle['close'] - reversal_price),
        details=json.dumps(details)
    )
