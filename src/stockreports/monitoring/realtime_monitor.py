# src/stockreports/monitoring/realtime_monitor.py
import logging
import time
from pathlib import Path
import re
import requests
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import pytz
from datetime import datetime
from typing import Optional

# Assuming settings are in src/stockreports/config/settings.py
# This relative import is tricky. A better project structure might be needed,
# but for now, we will use a path manipulation approach.
import sys
# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[3]
sys.path.append(str(project_root))

from src.stockreports.config import settings
from src.stockreports.utils.email_utils import send_email

# --- Basic Setup ---
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- Global State ---
# This will hold the high-confidence precursor combinations learned from the report
HIGH_CONFIDENCE_PRECURSORS = []
# This will hold the recent data for analysis
DATA_CACHE = pd.DataFrame()


def find_latest_report(reports_dir: Path, pattern: str) -> Optional[Path]:
    """Finds the most recent report file based on the timestamp in the filename."""
    report_files = list(reports_dir.glob(pattern))
    if not report_files:
        logging.warning(f"No analysis reports found in '{reports_dir}' matching '{pattern}'.")
        return None

    # Extract timestamps and find the latest
    latest_file = max(report_files, key=lambda f: f.stat().st_mtime)
    logging.info(f"Found latest analysis report: {latest_file.name}")
    return latest_file


def parse_precursors_from_report(report_path: Path) -> list[str]:
    """
    Parses the 'Precursor Combination Analysis' section of a markdown report
    to extract high-confidence precursor signal combinations.
    """
    if not report_path.exists():
        logging.error(f"Report file not found: {report_path}")
        return []

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        logging.error(f"Could not read report file {report_path}: {e}")
        return []

    # Use regex to find the table and then parse its rows
    table_match = re.search(
        r"### Precursor Combination Analysis\n\n(.*?)\n\n", content, re.DOTALL
    )
    if not table_match:
        logging.warning("Could not find 'Precursor Combination Analysis' section in the report.")
        return []

    table_str = table_match.group(1)
    lines = table_str.strip().split("\n")

    # Expecting a header like | Combination | Count | Frequency |
    if len(lines) < 3:
        logging.warning("Precursor table has insufficient data.")
        return []

    precursors = []
    # Skip header and separator lines
    for line in lines[2:]:
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) == 3:
            combination, _, frequency_str = parts
            try:
                # Frequency is like '15.79%'
                frequency = float(frequency_str.replace("%", ""))
                if frequency >= settings.HIGH_CONFIDENCE_THRESHOLD_PERCENT:
                    precursors.append(combination)
            except ValueError:
                continue  # Ignore lines that can't be parsed

    logging.info(f"Loaded {len(precursors)} high-confidence precursors: {precursors}")
    return precursors


def fetch_intraday_data() -> Optional[pd.DataFrame]:
    """Fetches the latest intraday data from the API."""
    try:
        # The API requires dynamic 'from' and 'to' timestamps.
        params = settings.API_PARAMS.copy()
        
        # Set 'to' to the current time.
        params["to"] = int(time.time())

        # Set 'from' to 8:45 AM of the current day in Vietnam's timezone.
        vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        now_vn = datetime.now(vn_tz)
        from_dt = now_vn.replace(hour=8, minute=45, second=0, microsecond=0)
        params["from"] = int(from_dt.timestamp())

        response = requests.get(
            settings.API_BASE_URL,
            params=params,
            headers=settings.API_HEADERS,
            timeout=10
        )
        response.raise_for_status()
        
        # The new API returns a dictionary of lists, not a list of dictionaries
        data = response.json()
        if not data.get("t"):
            logging.warning("API returned no data.")
            return None

        df = pd.DataFrame(data)
        # Ensure all expected columns are present
        if not all(col in df.columns for col in ["t", "o", "h", "l", "c", "v"]):
            logging.error("API response is missing expected columns.")
            return None

        df = df[["t", "o", "h", "l", "c", "v"]]
        df.columns = ["time", "open", "high", "low", "close", "volume"]

        # Convert timestamp to datetime objects
        df["time"] = pd.to_datetime(df["time"], unit="s").dt.tz_localize("UTC").dt.tz_convert("Asia/Ho_Chi_Minh")
        df = df.sort_values("time").reset_index(drop=True)
        return df

    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        return None
    except Exception as e:
        logging.error(f"Error processing data from API: {e}")
        return None

def analyze_live_data(df: pd.DataFrame):
    """Analyzes the latest data point for precursor signals."""
    if df.empty or len(df) < 20:
        logging.info("Not enough data to perform analysis.")
        return

    latest = df.iloc[-1]
    logging.info(
        f"Analyzing data point: {latest['time']} | "
        f"Price: {latest['close']:.2f} (H: {latest['high']:.2f}, L: {latest['low']:.2f}) | "
        f"Volume: {latest['volume']}"
    )

    # --- Calculate Indicators for the latest point ---
    # This part needs to be efficient, only calculating for the new data.
    # For simplicity in this example, we recalculate on a rolling window.
    window = df.tail(30).copy() # Use a rolling window for calculations

    # MA Crossover
    window["MA5"] = window["close"].rolling(window=5).mean()
    window["MA10"] = window["close"].rolling(window=10).mean()
    latest_calcs = window.iloc[-1]
    prev_calcs = window.iloc[-2]

    ma_crossed = (prev_calcs["MA5"] < prev_calcs["MA10"]) and (latest_calcs["MA5"] > latest_calcs["MA10"])

    # Volume Spike
    volume_spike = latest_calcs["volume"] > window["volume"].iloc[:-1].mean() * 2.5

    # Ichimoku Cloud (Simplified for one point)
    # Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
    tenkan_sen = (window['high'].rolling(window=9).max() + window['low'].rolling(window=9).min()) / 2
    # Kijun-sen (Base Line): (26-period high + 26-period low) / 2
    kijun_sen = (window['high'].rolling(window=26).max() + window['low'].rolling(window=26).min()) / 2
    
    ichimoku_bullish_cross = (tenkan_sen.iloc[-1] > kijun_sen.iloc[-1]) and \
                             (tenkan_sen.iloc[-2] < kijun_sen.iloc[-2])

    # --- New Indicator: Trend Strength ---
    trend_strength_signal = False
    if len(df) >= 2:
        prev_candle = df.iloc[-2]
        latest_candle = df.iloc[-1]

        # Condition 1: Sequential Trend
        latest_is_up = latest_candle['close'] > latest_candle['open']
        prev_is_up = prev_candle['close'] > prev_candle['open']
        latest_is_down = latest_candle['close'] < latest_candle['open']
        prev_is_down = prev_candle['close'] < prev_candle['open']
        
        same_trend = (latest_is_up and prev_is_up) or (latest_is_down and prev_is_down)

        if same_trend:
            # Condition 2: Range Sum (A)
            range_latest = abs(latest_candle['close'] - latest_candle['open'])
            range_prev = abs(prev_candle['close'] - prev_candle['open'])
            A = range_latest + range_prev
            range_sum_ok = A >= 3

            # Condition 3: Volatility Check (B)
            highest_high = max(latest_candle['high'], prev_candle['high'])
            lowest_low = min(latest_candle['low'], prev_candle['low'])
            B = highest_high - lowest_low
            volatility_ok = (B - A) < 1

            if range_sum_ok and volatility_ok:
                trend_strength_signal = True

    # --- Check for Precursor Combinations and Send Alerts ---
    active_signals = []
    if ma_crossed:
        active_signals.append("MA Cross")
    if volume_spike:
        active_signals.append("Volume Spike")
    if ichimoku_bullish_cross:
        active_signals.append("Ichimoku")
    if trend_strength_signal:
        active_signals.append("Trend Strength")

    if not active_signals:
        return

    # Any detected combination (except "None") will now trigger an alert.
    combination_str = " + ".join(sorted(active_signals))
    
    # Determine if the signal is "High-Confidence" based on historical data for logging purposes
    is_high_confidence = combination_str in HIGH_CONFIDENCE_PRECURSORS
    confidence_level = "High-Confidence" if is_high_confidence else "Standard"

    message = (
        f"[{confidence_level.upper()} SIGNAL] Precursor combination detected: {combination_str}. "
        f"Price: {latest_calcs['close']:.2f} at {latest_calcs['time'].strftime('%H:%M:%S')}"
    )
    logging.warning(message)

    # Send an email notification for any detected signal
    email_subject = f"Stock Alert ({confidence_level}): {combination_str} for {settings.API_PARAMS.get('symbol', 'VN30')}"
    email_body = (
        f"A {confidence_level.lower()} precursor pattern was detected for {settings.API_PARAMS.get('symbol', 'VN30')}.\n\n"
        f"Pattern: {combination_str}\n"
        f"Time: {latest_calcs['time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Price: {latest_calcs['close']:.2f}\n"
        f"Volume: {latest_calcs['volume']}\n\n"
        "This is an automated alert."
    )
    send_email(email_subject, email_body)

def main():
    """Main function to run the real-time monitor."""
    global HIGH_CONFIDENCE_PRECURSORS, DATA_CACHE

    # --- Initial Setup ---
    # Determine the absolute path to the reports directory
    reports_dir = project_root / settings.REPORTS_DIR
    
    latest_report = find_latest_report(reports_dir, settings.LATEST_REPORT_PATTERN)
    if latest_report:
        HIGH_CONFIDENCE_PRECURSORS = parse_precursors_from_report(latest_report)
    else:
        logging.warning("Continuing without historical precursor data.")

    logging.info("Starting real-time stock monitor...")

    # --- Main Loop ---
    while True:
        try:
            new_data = fetch_intraday_data()

            if new_data is not None and not new_data.empty:
                # Append new data and remove duplicates
                DATA_CACHE = pd.concat([DATA_CACHE, new_data]).drop_duplicates(subset=['time'], keep='last')
                # Keep the cache size manageable, e.g., last 2 hours of data (120 points)
                DATA_CACHE = DATA_CACHE.tail(120)
                
                analyze_live_data(DATA_CACHE)

            # Wait for the next interval
            time.sleep(settings.MONITORING_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logging.info("Stopping real-time monitor.")
            break
        except Exception as e:
            logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            time.sleep(settings.MONITORING_INTERVAL_SECONDS * 2) # Wait longer after an error


if __name__ == "__main__":
    main()
