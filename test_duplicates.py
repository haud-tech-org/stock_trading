#!/usr/bin/env python3
"""
Test script to verify enhanced duplicate detection in stockreports.
"""

from stockreports import HARExtractor, StockDataAggregator
import tempfile
import json
from pathlib import Path

def test_duplicate_detection():
    print("🧪 Testing Enhanced Duplicate Detection")
    
    # Test aggregator with existing data
    print("\n📊 Testing StockDataAggregator with enhanced timestamp deduplication...")
    aggregator = StockDataAggregator(
        "d:/Temp/project/project/data/har_responses",
        "d:/Temp/project/duplicate_test_reports"
    )
    
    # Test symbol detection
    symbols = aggregator.extract_symbols_from_files()
    print(f"✅ Found symbols: {symbols}")
    
    for symbol in symbols:
        print(f"\n📈 Processing {symbol} with enhanced deduplication...")
        data, files, columns = aggregator.aggregate_symbol_data(symbol)
        print(f"✅ Final unique records for {symbol}: {len(data)} from {files} files")
        print(f"📋 Columns: {list(columns.keys())}")
        
        # Show some sample timestamps to verify no duplicates
        if 't' in columns and data:
            ordered_keys = list(columns.keys())
            t_index = ordered_keys.index('t')
            sample_timestamps = [row[0][t_index] for row in data[:5]]
            print(f"📅 Sample timestamps: {sample_timestamps}")
    
    print("\n🎉 Enhanced duplicate detection test completed!")

def analyze_timestamp_patterns():
    print("\n🔍 Analyzing timestamp patterns in response files...")
    
    responses_dir = Path("d:/Temp/project/project/data/har_responses")
    vn30_files = list(responses_dir.glob("*_VN30.json"))
    
    timestamp_sets = {}
    
    for file_path in vn30_files[:5]:  # Check first 5 files
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            if 't' in data and isinstance(data['t'], list):
                timestamps = set(data['t'])
                timestamp_sets[file_path.name] = timestamps
                print(f"📄 {file_path.name}: {len(timestamps)} unique timestamps")
                
        except Exception as e:
            print(f"❌ Error reading {file_path.name}: {e}")
    
    # Check for overlaps
    file_names = list(timestamp_sets.keys())
    for i, file1 in enumerate(file_names):
        for file2 in file_names[i+1:]:
            overlap = timestamp_sets[file1] & timestamp_sets[file2]
            if overlap:
                print(f"⚠️  {file1} and {file2} share {len(overlap)} timestamps")
                print(f"   Sample overlapping timestamps: {list(overlap)[:3]}")
            else:
                print(f"✅ {file1} and {file2} have no overlapping timestamps")

if __name__ == "__main__":
    test_duplicate_detection()
    analyze_timestamp_patterns()
