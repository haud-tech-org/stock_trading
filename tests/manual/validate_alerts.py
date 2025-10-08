# tests/manual/validate_alerts.py
import logging
from pathlib import Path
import sys
import pandas as pd
from datetime import timedelta

# Add project root to Python path
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

from src.stockreports.config import settings
from src.stockreports.monitoring.realtime_monitor import (
    fetch_intraday_data,
    find_latest_report,
    parse_precursors_from_report,
)

logging.basicConfig(
    level="INFO", format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Validation Parameters ---
# An alert is "successful" if the price rises by at least this amount...
PRICE_GAIN_THRESHOLD = 2.0
# ...within this number of minutes.
TIME_WINDOW_MINUTES = 20


def find_alerts(df: pd.DataFrame) -> list:
    """Finds all timestamps in the DataFrame that would trigger an alert."""
    if df.empty or len(df) < 30:
        return []

    # Calculate all indicators
    df["MA5"] = df["close"].rolling(window=5).mean()
    df["MA10"] = df["close"].rolling(window=10).mean()
    df["AvgVolume20"] = df["volume"].rolling(window=20).mean()
    tenkan_sen = (df['high'].rolling(window=9).max() + df['low'].rolling(window=9).min()) / 2
    kijun_sen = (df['high'].rolling(window=26).max() + df['low'].rolling(window=26).min()) / 2

    # Identify signal events
    ma_crossed = (df["MA5"] > df["MA10"]) & (df["MA5"].shift(1) < df["MA10"].shift(1))
    volume_spike = df["volume"] > (df["AvgVolume20"].shift(1) * 2.5)
    ichimoku_bullish_cross = (tenkan_sen > kijun_sen) & (tenkan_sen.shift(1) < kijun_sen.shift(1))

    # --- New Indicator: Trend Strength (vectorized) ---
    # Condition 1: Sequential Trend
    is_up = df['close'] > df['open']
    is_down = df['close'] < df['open']
    same_trend = ((is_up & is_up.shift(1)) | (is_down & is_down.shift(1))).fillna(False)

    # Condition 2: Range Sum (A)
    candle_range = (df['close'] - df['open']).abs()
    A = candle_range + candle_range.shift(1)
    range_sum_ok = A >= 3

    # Condition 3: Volatility Check (B)
    highest_high = df['high'].rolling(window=2).max()
    lowest_low = df['low'].rolling(window=2).min()
    B = highest_high - lowest_low
    volatility_ok = (B - A) < 1
    
    trend_strength_signal = same_trend & range_sum_ok & volatility_ok

    alerts = []
    for i in range(26, len(df)):
        active_signals = []
        if ma_crossed.iloc[i]:
            active_signals.append("MA Cross")
        if volume_spike.iloc[i]:
            active_signals.append("Volume Spike")
        if ichimoku_bullish_cross.iloc[i]:
            active_signals.append("Ichimoku")
        if trend_strength_signal.iloc[i]:
            active_signals.append("Trend Strength")

        if active_signals:
            alerts.append({
                "index": i,
                "time": df.iloc[i]["time"],
                "price": df.iloc[i]["close"],
                "combination": " + ".join(sorted(active_signals)),
            })
    return alerts


def validate_alerts(df: pd.DataFrame, alerts: list) -> pd.DataFrame:
    """Checks each alert against the success criteria."""
    results = []
    for alert in alerts:
        alert_time = alert["time"]
        alert_price = alert["price"]
        
        # Define the 15-minute window after the alert
        window_end_time = alert_time + timedelta(minutes=TIME_WINDOW_MINUTES)
        
        # Get the data within that window
        future_data = df[(df["time"] > alert_time) & (df["time"] <= window_end_time)]

        outcome = "Incomplete"  # Default if not enough time has passed
        max_gain = 0
        
        if not future_data.empty:
            # Find the highest price reached in the window
            highest_price_in_window = future_data["high"].max()
            max_gain = highest_price_in_window - alert_price
            
            if max_gain >= PRICE_GAIN_THRESHOLD:
                outcome = "Success"
            else:
                # If the window is complete, but the threshold wasn't met, it's a Fail
                if future_data["time"].max() >= window_end_time:
                    outcome = "Fail"

        results.append({
            "Time": alert_time.strftime('%H:%M:%S'),
            "Combination": alert["combination"],
            "Alert Price": f"{alert_price:.2f}",
            "Max Gain in 15min": f"{max_gain:.2f}",
            "Outcome": outcome,
        })
        
    return pd.DataFrame(results)


def generate_report(results_df: pd.DataFrame):
    """Generates a markdown report from the validation results."""
    report_path = project_root / "alert_accuracy_report.md"
    
    success_count = len(results_df[results_df["Outcome"] == "Success"])
    fail_count = len(results_df[results_df["Outcome"] == "Fail"])
    incomplete_count = len(results_df[results_df["Outcome"] == "Incomplete"])
    total_evaluated = success_count + fail_count
    
    accuracy = (success_count / total_evaluated * 100) if total_evaluated > 0 else 0

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Alert Accuracy Backtest Report\n\n")
        f.write(f"**Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}\n\n")
        f.write("This report analyzes the performance of the trading alerts generated by the monitoring script based on today's intraday data.\n\n")
        
        f.write("## Success Criteria\n\n")
        f.write(f"- **Condition**: An alert is considered a 'Success' if the price increases by at least **{PRICE_GAIN_THRESHOLD:.2f} points**.\n")
        f.write(f"- **Timeframe**: This price gain must occur within **{TIME_WINDOW_MINUTES} minutes** following the alert.\n\n")

        f.write("## Summary\n\n")
        f.write(f"- **Total Alerts Generated**: {len(results_df)}\n")
        f.write(f"- **Successful Alerts**: {success_count}\n")
        f.write(f"- **Failed Alerts**: {fail_count}\n")
        f.write(f"- **Incomplete (not enough time to evaluate)**: {incomplete_count}\n")
        f.write(f"- **Success Rate (Accuracy)**: **{accuracy:.2f}%**\n\n")

        f.write("## Detailed Results\n\n")
        f.write(results_df.to_markdown(index=False))
        f.write("\n")

    logging.info(f"Accuracy report generated: {report_path}")


def main():
    """Main function to run the validation script."""
    logging.info("Starting alert validation script...")
    
    todays_data = fetch_intraday_data()
    if todays_data is None or todays_data.empty:
        logging.error("Could not fetch data for today. Aborting validation.")
        return

    alerts = find_alerts(todays_data)
    if not alerts:
        logging.info("No alerts were generated today. Nothing to validate.")
        return
        
    results_df = validate_alerts(todays_data, alerts)
    generate_report(results_df)


if __name__ == "__main__":
    main()
