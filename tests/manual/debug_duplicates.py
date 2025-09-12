#!/usr/bin/env python3
"""
Debug script for duplicate detection functionality.

This script helps developers debug duplicate detection issues by:
- Testing HAR extractor duplicate detection
- Testing aggregator timestamp and hash-based deduplication
- Analyzing existing data for duplicate patterns
- Providing detailed diagnostic output

Usage:
    python tests/manual/debug_duplicates.py
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add source directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from stockreports import HARExtractor, StockDataAggregator
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Running in standalone mode without stockreports imports")
    IMPORTS_AVAILABLE = False


def analyze_response_file_duplicates(file_path):
    """Analyze a response file for potential duplicates."""
    print(f"\n🔍 Analyzing: {file_path}")
    print("-" * 40)
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict) or 't' not in data:
            print("⚠️  Invalid data format - no timestamp array 't'")
            return
        
        timestamps = data.get('t', [])
        if not timestamps:
            print("⚠️  No timestamps found")
            return
        
        print(f"Total entries: {len(timestamps)}")
        
        # Check for timestamp duplicates
        timestamp_counts = {}
        for ts in timestamps:
            timestamp_counts[ts] = timestamp_counts.get(ts, 0) + 1
        
        duplicates = {ts: count for ts, count in timestamp_counts.items() if count > 1}
        
        if duplicates:
            print(f"❌ Timestamp duplicates found: {len(duplicates)}")
            for ts, count in duplicates.items():
                print(f"   - {ts}: {count} occurrences")
        else:
            print("✅ No timestamp duplicates")
        
        # Check for potential data row duplicates
        if all(key in data for key in ['o', 'h', 'l', 'c', 'v']):
            rows = list(zip(
                timestamps,
                data.get('o', []),
                data.get('h', []),
                data.get('l', []),
                data.get('c', []),
                data.get('v', [])
            ))
            
            row_counts = {}
            for row in rows:
                row_key = str(row[1:])  # Exclude timestamp for duplicate check
                row_counts[row_key] = row_counts.get(row_key, 0) + 1
            
            data_duplicates = {key: count for key, count in row_counts.items() if count > 1}
            
            if data_duplicates:
                print(f"⚠️  Potential data row duplicates: {len(data_duplicates)}")
                for key, count in list(data_duplicates.items())[:3]:  # Show first 3
                    print(f"   - Data pattern appears {count} times")
            else:
                print("✅ No data row duplicates detected")
        
    except Exception as e:
        print(f"❌ Error analyzing file: {e}")


def test_har_extractor_duplicates():
    """Test HAR extractor duplicate detection if available."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping HAR extractor test - imports not available")
        return
    
    print(f"\n🧪 Testing HAR Extractor Duplicate Detection")
    print("=" * 50)
    
    # Look for existing HAR files
    har_directories = [
        "project/sources/har",
        "tests/fixtures/har_files",
    ]
    
    har_dir = None
    for test_dir in har_directories:
        if Path(test_dir).exists():
            har_files = list(Path(test_dir).glob("*.har"))
            if har_files:
                har_dir = test_dir
                print(f"Found HAR files in: {har_dir}")
                break
    
    if not har_dir:
        print("⚠️  No HAR files found for testing")
        return
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Extracting to temporary directory: {temp_dir}")
            
            extractor = HARExtractor(har_dir, temp_dir)
            results = extractor.extract_all()
            
            print(f"✅ Extraction completed:")
            print(f"   - Files processed: {results.get('files_processed', 'N/A')}")
            print(f"   - Entries extracted: {results.get('entries_extracted', 'N/A')}")
            
            if hasattr(extractor, 'duplicate_count'):
                print(f"   - Duplicates detected: {extractor.duplicate_count}")
            else:
                print("   - Duplicate count not available")
    
    except Exception as e:
        print(f"❌ Error testing HAR extractor: {e}")
        import traceback
        traceback.print_exc()


def test_aggregator_duplicates():
    """Test aggregator duplicate detection if available."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping aggregator test - imports not available")
        return
    
    print(f"\n📊 Testing Aggregator Duplicate Detection")
    print("=" * 50)
    
    # Look for existing response files
    response_directories = [
        "final_validation_reports/responses/har_responses",
        "project/data/har_responses", 
        "tests/fixtures/expected_outputs",
    ]
    
    responses_dir = None
    for test_dir in response_directories:
        if Path(test_dir).exists():
            json_files = list(Path(test_dir).glob("*response*.json"))
            if json_files:
                responses_dir = test_dir
                print(f"Found response files in: {responses_dir}")
                break
    
    if not responses_dir:
        print("⚠️  No response files found for testing")
        return
    
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Processing to temporary directory: {temp_dir}")
            
            aggregator = StockDataAggregator(responses_dir, temp_dir)
            results = aggregator.process_all_symbols()
            
            if results:
                print(f"✅ Aggregation completed:")
                print(f"   - Symbols processed: {len([k for k, v in results.items() if isinstance(v, dict)])}")
                
                for symbol, data in results.items():
                    if isinstance(data, dict):
                        print(f"\n   📈 {symbol}:")
                        if "unique_records" in data:
                            print(f"      - Unique records: {data['unique_records']}")
                        if "timestamp_duplicates" in data:
                            print(f"      - Timestamp duplicates: {data['timestamp_duplicates']}")
                        if "hash_duplicates" in data:
                            print(f"      - Hash duplicates: {data['hash_duplicates']}")
            else:
                print("⚠️  No aggregation results")
    
    except Exception as e:
        print(f"❌ Error testing aggregator: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main debug function."""
    print("🐛 Duplicate Detection Debug Tool")
    print("=" * 60)
    
    # Analyze existing response files for duplicates
    response_directories = [
        "final_validation_reports/responses/har_responses",
        "project/data/har_responses",
    ]
    
    for test_dir in response_directories:
        if Path(test_dir).exists():
            print(f"\n📂 Analyzing response files in: {test_dir}")
            
            response_files = list(Path(test_dir).glob("*response*.json"))
            if response_files:
                print(f"Found {len(response_files)} response files")
                
                # Analyze first few files
                for file_path in response_files[:3]:
                    analyze_response_file_duplicates(file_path)
                
                if len(response_files) > 3:
                    print(f"\n... and {len(response_files) - 3} more files")
            else:
                print("No response files found")
            break
    
    # Test HAR extractor duplicate detection
    test_har_extractor_duplicates()
    
    # Test aggregator duplicate detection  
    test_aggregator_duplicates()
    
    print(f"\n✅ Duplicate detection debug session completed!")


if __name__ == "__main__":
    main()
