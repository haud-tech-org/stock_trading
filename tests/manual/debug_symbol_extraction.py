#!/usr/bin/env python3
"""
Debug script for symbol extraction functionality.

This script helps developers debug symbol extraction issues by:
- Testing regex patterns against filenames
- Validating directory structure
- Testing aggregator symbol discovery
- Providing detailed diagnostic output

Usage:
    python tests/manual/debug_symbol_extraction.py
"""

import os
import sys
import re
from pathlib import Path

# Add source directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from stockreports.aggregators import StockDataAggregator
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Running in standalone mode without stockreports imports")
    IMPORTS_AVAILABLE = False


def test_regex_patterns():
    """Test regex patterns for symbol extraction."""
    print("🧪 Testing Regex Patterns")
    print("=" * 40)
    
    test_cases = [
        ("all-25-11-09_response_1_VNINDEX.json", "VNINDEX", True),
        ("VN30-1m_response_85_VNINDEX.json", "VNINDEX", True),
        ("test_response_42_VN30.json", "VN30", True),
        ("response_1_HPG.json", "HPG", True),
        ("not_a_response_file.json", None, False),
        ("response_VNINDEX.json", None, False),  # Missing number
        ("response_1_VNINDEX.txt", None, False),  # Wrong extension
    ]
    
    pattern = r'response_\d+_([^.]+)\.json$'
    
    for filename, expected_symbol, should_match in test_cases:
        match = re.search(pattern, filename)
        
        if should_match:
            if match:
                extracted_symbol = match.group(1)
                status = "✅" if extracted_symbol == expected_symbol else "❌"
                print(f"{status} {filename}")
                print(f"    Expected: {expected_symbol}, Got: {extracted_symbol}")
            else:
                print(f"❌ {filename}")
                print(f"    Expected match but got None")
        else:
            status = "✅" if not match else "❌"
            print(f"{status} {filename}")
            if match:
                print(f"    Unexpected match: {match.group(1)}")


def test_file_discovery(directory_path):
    """Test file discovery in given directory."""
    print(f"\n🔍 Testing File Discovery: {directory_path}")
    print("=" * 40)
    
    directory = Path(directory_path)
    print(f"Directory: {directory.absolute()}")
    print(f"Exists: {directory.exists()}")
    
    if not directory.exists():
        print("❌ Directory does not exist")
        return []
    
    json_files = list(directory.glob('*.json'))
    print(f"JSON files found: {len(json_files)}")
    
    response_files = []
    for file_path in json_files:
        print(f"\nFile: {file_path.name}")
        
        if 'response_' in file_path.name:
            match = re.search(r'response_\d+_([^.]+)\.json$', file_path.name)
            if match:
                symbol = match.group(1)
                print(f"  ✅ Symbol extracted: {symbol}")
                response_files.append((file_path.name, symbol))
            else:
                print(f"  ⚠️  Contains 'response_' but no regex match")
        else:
            print(f"  ⏭️  No 'response_' in filename - skipped")
    
    return response_files


def test_aggregator_integration(directory_path):
    """Test the aggregator symbol extraction if imports are available."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping aggregator test - imports not available")
        return
    
    print(f"\n🎯 Testing Aggregator Integration")
    print("=" * 40)
    
    try:
        aggregator = StockDataAggregator(directory_path, "temp_test_output")
        symbols = aggregator.extract_symbols_from_files()
        print(f"Aggregator found symbols: {symbols}")
        print(f"Number of unique symbols: {len(symbols)}")
        
        if symbols:
            print("Symbol details:")
            for symbol in symbols:
                print(f"  - {symbol} (type: {type(symbol).__name__}, length: {len(symbol)})")
        
    except Exception as e:
        print(f"❌ Error testing aggregator: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main debug function."""
    print("🐛 Symbol Extraction Debug Tool")
    print("=" * 50)
    
    # Test regex patterns
    test_regex_patterns()
    
    # Test with common test directories
    test_directories = [
        "final_validation_reports/responses/har_responses",
        "tests/fixtures/har_files",
        "data/har_responses",
    ]
    
    for test_dir in test_directories:
        if Path(test_dir).exists():
            response_files = test_file_discovery(test_dir)
            if response_files:
                test_aggregator_integration(test_dir)
            break
    else:
        print(f"\n⚠️  No test directories found. Tried:")
        for test_dir in test_directories:
            print(f"   - {test_dir}")
        print("\nTo test with your data, create some response files or update the directory paths.")
    
    print(f"\n✅ Debug session completed!")


if __name__ == "__main__":
    main()
