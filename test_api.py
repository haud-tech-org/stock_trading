#!/usr/bin/env python3
"""
Quick test script for the stockreports package API.
"""

from stockreports import HARExtractor, StockDataAggregator

def main():
    print("🧪 Testing StockReports Package API")
    
    # Test aggregator
    print("\n📊 Testing StockDataAggregator...")
    aggregator = StockDataAggregator(
        "d:/Temp/project/project/data/har_responses",
        "d:/Temp/project/api_test_reports"
    )
    
    # Test symbol detection
    symbols = aggregator.extract_symbols_from_files()
    print(f"✅ Found symbols: {symbols}")
    
    # Quick processing test
    if symbols:
        symbol = symbols[0]
        print(f"\n📈 Testing data processing for {symbol}...")
        data, files, columns = aggregator.aggregate_symbol_data(symbol)
        print(f"✅ Processed {len(data)} records from {files} files")
        print(f"📋 Detected columns: {list(columns.keys())}")
    
    print("\n🎉 API test completed successfully!")

if __name__ == "__main__":
    main()
