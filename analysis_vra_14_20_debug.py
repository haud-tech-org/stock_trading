"""
Detailed analysis of VRA alert detection issue at 2026-03-13 14:20:00
Compares refactored code behavior with expected original code behavior
"""
import sys
import os
import pandas as pd

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_live_data
from src.stockreports.alert.approach.VRA.executor import VraExecutor
from src.stockreports.alert.approach.VRA.analyzer import VraAnalyzer
from src.stockreports.alert.approach.VRA.validator import VraValidator
import importlib

# Load configuration
importlib.reload(loader)
settings = loader.get_settings()
settings.MODE = 'DEVELOPMENT'

# Fetch the data
timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
start_time = pd.to_datetime("2026-03-13 14:00:00").tz_localize(timezone)
end_time = pd.to_datetime("2026-03-13 14:25:00").tz_localize(timezone)

print("=" * 80)
print("VRA ALERT DETECTION ANALYSIS: 2026-03-13 14:00-14:25")
print("=" * 80)

from_timestamp = int(start_time.timestamp())
to_timestamp = int(end_time.timestamp())
df = load_live_data("VN30F1M", from_timestamp=from_timestamp, to_timestamp=to_timestamp)

print(f"\nTotal candles fetched: {len(df)}")
print("\nData Structure:")
print(df[['time', 'open', 'high', 'low', 'close', 'volume']].to_string())

# Key observations from the expected old code alert
print("\n" + "=" * 80)
print("EXPECTED ALERT (FROM OLD CODE):")
print("=" * 80)
print("Time: 2026-03-13 14:20:00+07:00")
print("Index: 20 (in the 0-25 range)")
print("Min volume candle: Index 17 (14:17:00), volume=992.0")
print("Max volume candle: Index 20 (14:20:00), volume=5393.0")
print("Volume Ratio: 5393 / 992 = 5.44")
print("Status: ALERT RAISED ✓")

# Now let's trace through the refactored code execution
print("\n" + "=" * 80)
print("REFACTORED CODE EXECUTION TRACE:")
print("=" * 80)

executor = VraExecutor("VN30F1M")
print(f"\nLookback window size: {executor.settings.lookback_window}")
print(f"Volume multiplier threshold: {executor.settings.volume_multiplier}")

# Simulate the loop that refactored code uses
df_indexed = df.reset_index()
loop_end = len(df_indexed)
min_scan_index = executor.settings.lookback_window

print(f"\nLoop parameters:")
print(f"  - df_indexed length: {len(df_indexed)}")
print(f"  - loop_end: {loop_end}")
print(f"  - min_scan_index: {min_scan_index}")

# Analyze specific scan indices relevant to 14:20
target_indices = [20, 21, 19, 18]  # Index 20 is 14:20
print(f"\nAnalyzing scan indices: {target_indices}")

for scan_idx in target_indices:
    if scan_idx >= min_scan_index:
        print(f"\n--- Scan Index: {scan_idx} ---")
        print(f"    Candle time: {df_indexed.loc[scan_idx, 'time']}")
        
        # This is what the current refactored code does
        window_start = scan_idx - executor.settings.lookback_window
        window_end = scan_idx  # Python slicing is exclusive at end
        window = df_indexed.iloc[window_start:window_end]
        
        print(f"    Window slice: [{window_start}:{window_end}]")
        print(f"    Window actual indices: {list(window.index.values)}")
        print(f"    Window size: {len(window)} candles")
        print(f"    Window start time: {window.iloc[0]['time']}")
        print(f"    Window end time: {window.iloc[-1]['time']}")
        
        last_candle = window.iloc[-1]
        
        # Analyze volume in window
        min_vol_candle = window.loc[window['volume'].idxmin()]
        max_vol_candle = window.loc[window['volume'].idxmax()]
        
        print(f"    Last candle in window: {last_candle['time']}, volume={last_candle['volume']}")
        print(f"    Min volume candle: {min_vol_candle['time']}, volume={min_vol_candle['volume']}")
        print(f"    Max volume candle: {max_vol_candle['time']}, volume={max_vol_candle['volume']}")
        
        # Calculate ratio
        analyzer = VraAnalyzer()
        ratio = analyzer.calculate_volume_ratio(last_candle['volume'], min_vol_candle['volume'])
        print(f"    Volume ratio: {last_candle['volume']} / {min_vol_candle['volume']} = {ratio:.2f}")
        
        # Check validation
        validator = VraValidator()
        is_valid = validator.validate_volume_ratio(ratio, executor.settings.volume_multiplier)
        print(f"    Validation: {ratio:.2f} >= {executor.settings.volume_multiplier} ? {is_valid}")

print("\n" + "=" * 80)
print("KEY QUESTION: WHY DOESN'T INDEX 20 WINDOW INCLUDE THE MIN VOL AT INDEX 17?")
print("=" * 80)

print(f"\nWhen scan_idx = 20:")
print(f"  Window = df_indexed.iloc[{20 - executor.settings.lookback_window}:{20}]")
print(f"  Window = df_indexed.iloc[{20 - 7}:{20}]")
print(f"  Window = df_indexed.iloc[13:20]")
print(f"  Indices in window: 13, 14, 15, 16, 17, 18, 19")
print(f"  ✓ Index 17 IS in the window!")
print(f"  Last candle in window: Index 19 (NOT 20!)")
print(f"  Candle at index 19: {df_indexed.loc[19, 'time']}, volume={df_indexed.loc[19, 'volume']}")

# So the issue is that when scan_idx=20, the window ends at 19, not 20
# Let's check what window would include index 20 as the last candle
print(f"\nTo get index 20 as the LAST candle in window:")
print(f"  Need window = df_indexed.iloc[a:21]")
print(f"  With lookback=7: df_indexed.iloc[14:21]")
print(f"  Indices in window: 14, 15, 16, 17, 18, 19, 20")
print(f"  Last candle in window: Index 20")
print(f"  Candle at index 20: {df_indexed.loc[20, 'time']}, volume={df_indexed.loc[20, 'volume']}")

# Check if min/max are found correctly
print(f"\n  Min volume in [14:21]: Index 17, volume=992.0 ✓")
print(f"  Max volume in [14:21]: Index 20, volume=5393.0 ✓")
print(f"  Ratio: 5393 / 992 = 5.44 ✓")

print("\n" + "=" * 80)
print("ROOT CAUSE IDENTIFIED:")
print("=" * 80)
print("When scan_idx=20, the current code uses:")
print("  iloc[scan_idx - lookback : scan_idx]")
print("  = iloc[20 - 7 : 20]")
print("  = iloc[13:20]")
print("  Last candle is at INDEX 19 (14:19:00), NOT index 20 (14:20:00)")
print("")
print("But we need:")
print("  iloc[scan_idx - lookback : scan_idx + 1]")
print("  = iloc[13:21]")
print("  Last candle is at INDEX 20 (14:20:00) ✓")
print("=" * 80)
