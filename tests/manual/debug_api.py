#!/usr/bin/env python3
"""
Debug script for API functionality testing.

This script helps developers test and debug the public API by:
- Testing basic API initialization
- Testing symbol detection functionality  
- Testing data processing methods
- Testing error handling scenarios
- Providing detailed diagnostic output

Usage:
    python tests/manual/debug_api.py
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


def test_basic_initialization():
    """Test basic API class initialization."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping initialization test - imports not available")
        return
    
    print("\n🏗️  Testing API Initialization")
    print("=" * 40)
    
    try:
        # Test HARExtractor initialization
        print("Testing HARExtractor...")
        extractor = HARExtractor("test_dir")
        print(f"✅ Basic initialization: har_dir = {extractor.har_dir}")
        
        extractor = HARExtractor("test_dir", "output_dir")
        print(f"✅ With output dir: output_dir = {extractor.output_dir}")
        
        extractor = HARExtractor("test_dir", "output_dir", tz_name="Asia/Ho_Chi_Minh")
        print(f"✅ With timezone: timezone_name = {extractor.timezone_name}")
        
        # Test StockDataAggregator initialization
        print("\nTesting StockDataAggregator...")
        aggregator = StockDataAggregator("responses_dir", "output_dir")
        print(f"✅ Basic initialization: responses_dir = {aggregator.responses_dir}")
        print(f"✅ Output directory: output_dir = {aggregator.output_dir}")
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        import traceback
        traceback.print_exc()


def test_symbol_detection_api():
    """Test symbol detection API functionality."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping symbol detection test - imports not available")
        return
    
    print("\n🔍 Testing Symbol Detection API")
    print("=" * 40)
    
    # Look for existing response directories
    test_directories = [
        "final_validation_reports/responses/har_responses",
        "project/data/har_responses",
    ]
    
    test_dir = None
    for directory in test_directories:
        if Path(directory).exists():
            test_dir = directory
            break
    
    if not test_dir:
        print("⚠️  No response directories found for testing")
        # Create temporary test data
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = temp_dir
            print(f"Creating temporary test data in: {test_dir}")
            
            # Create test files
            test_files = [
                "sample_response_1_VNINDEX.json",
                "sample_response_2_VN30.json", 
                "sample_response_3_HPG.json",
            ]
            
            for filename in test_files:
                (Path(test_dir) / filename).write_text("{}")
            
            _test_symbol_api_with_directory(test_dir)
    else:
        print(f"Using existing directory: {test_dir}")
        _test_symbol_api_with_directory(test_dir)


def _test_symbol_api_with_directory(directory):
    """Helper to test symbol API with specific directory."""
    try:
        aggregator = StockDataAggregator(directory, "temp_output")
        
        # Test symbol extraction
        symbols = aggregator.extract_symbols_from_files()
        print(f"✅ Symbol extraction successful")
        print(f"   - Found {len(symbols)} symbols: {symbols}")
        print(f"   - Return type: {type(symbols).__name__}")
        
        # Validate return format
        if isinstance(symbols, list):
            print("✅ Returns list as expected")
            if all(isinstance(s, str) for s in symbols):
                print("✅ All symbols are strings")
            else:
                print("❌ Not all symbols are strings")
        else:
            print(f"❌ Expected list, got {type(symbols).__name__}")
        
        return symbols
        
    except Exception as e:
        print(f"❌ Symbol detection error: {e}")
        import traceback
        traceback.print_exc()
        return []


def test_data_processing_api():
    """Test data processing API functionality."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping data processing test - imports not available")
        return
    
    print("\n📊 Testing Data Processing API")
    print("=" * 40)
    
    # Create temporary test data
    with tempfile.TemporaryDirectory() as temp_dir:
        responses_dir = Path(temp_dir) / "responses"
        responses_dir.mkdir()
        
        # Create test data file
        test_data = {
            "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00", "2025-09-03 09:25:00"],
            "o": [1500.0, 1502.0, 1504.0],
            "h": [1505.0, 1507.0, 1509.0],
            "l": [1498.0, 1500.0, 1502.0],
            "c": [1502.0, 1505.0, 1507.0],
            "v": [1000, 1200, 1400]
        }
        
        test_file = responses_dir / "test_response_1_VNINDEX.json"
        test_file.write_text(json.dumps(test_data))
        
        try:
            aggregator = StockDataAggregator(str(responses_dir), str(Path(temp_dir) / "output"))
            
            # Test individual symbol processing
            print("Testing aggregate_symbol_data method...")
            symbol_data, files_count, detected_columns = aggregator.aggregate_symbol_data("VNINDEX")
            
            print(f"✅ Individual symbol processing successful")
            print(f"   - Data points: {len(symbol_data)}")
            print(f"   - Files processed: {files_count}")
            print(f"   - Detected columns: {list(detected_columns.keys())}")
            print(f"   - Data type: {type(symbol_data).__name__}")
            
            # Test full processing pipeline
            print("\nTesting process_all_symbols method...")
            results = aggregator.process_all_symbols()
            
            print(f"✅ Full processing successful")
            print(f"   - Results type: {type(results).__name__}")
            print(f"   - Symbols processed: {len([k for k, v in results.items() if isinstance(v, dict)])}")
            
            if "VNINDEX" in results:
                symbol_result = results["VNINDEX"]
                print(f"   - VNINDEX result keys: {list(symbol_result.keys())}")
            
        except Exception as e:
            print(f"❌ Data processing error: {e}")
            import traceback
            traceback.print_exc()


def test_error_handling_api():
    """Test API error handling capabilities."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping error handling test - imports not available")
        return
    
    print("\n🛡️  Testing Error Handling API")
    print("=" * 40)
    
    try:
        # Test with non-existent directory
        print("Testing with non-existent directory...")
        aggregator = StockDataAggregator("nonexistent_directory", "output")
        symbols = aggregator.extract_symbols_from_files()
        print(f"✅ Handled non-existent directory: returned {symbols}")
        
        # Test with empty directory
        print("Testing with empty directory...")
        with tempfile.TemporaryDirectory() as temp_dir:
            aggregator = StockDataAggregator(temp_dir, "output")
            symbols = aggregator.extract_symbols_from_files()
            print(f"✅ Handled empty directory: returned {symbols}")
        
        # Test with invalid data files
        print("Testing with invalid data files...")
        with tempfile.TemporaryDirectory() as temp_dir:
            responses_dir = Path(temp_dir)
            
            # Create invalid JSON file
            (responses_dir / "test_response_1_INVALID.json").write_text("invalid json")
            
            aggregator = StockDataAggregator(str(responses_dir), "output")
            symbols = aggregator.extract_symbols_from_files()
            print(f"✅ Found symbols despite invalid JSON: {symbols}")
            
            # Test processing with invalid data
            results = aggregator.process_all_symbols()
            print(f"✅ Processing handled invalid data: {type(results).__name__}")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()


def test_real_world_usage():
    """Test realistic usage scenarios."""
    if not IMPORTS_AVAILABLE:
        print("\n⚠️  Skipping real-world test - imports not available")
        return
    
    print("\n🌍 Testing Real-World Usage Patterns")
    print("=" * 40)
    
    # Look for real data
    real_data_dirs = [
        "final_validation_reports/responses/har_responses",
        "project/data/har_responses",
    ]
    
    real_dir = None
    for directory in real_data_dirs:
        if Path(directory).exists():
            json_files = list(Path(directory).glob("*response*.json"))
            if json_files:
                real_dir = directory
                break
    
    if real_dir:
        print(f"Testing with real data from: {real_dir}")
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Typical user workflow
                aggregator = StockDataAggregator(real_dir, temp_dir)
                
                # Step 1: Discover symbols
                symbols = aggregator.extract_symbols_from_files()
                print(f"✅ Step 1 - Symbol discovery: {len(symbols)} symbols")
                
                # Step 2: Process all symbols
                results = aggregator.process_all_symbols()
                print(f"✅ Step 2 - Data processing: {len([k for k in results.keys() if isinstance(results[k], dict)])} symbols processed")
                
                # Step 3: Check outputs
                output_files = list(Path(temp_dir).glob("*.md"))
                print(f"✅ Step 3 - Output generation: {len(output_files)} report files")
                
                # Step 4: Verify content
                if output_files:
                    sample_file = output_files[0]
                    content = sample_file.read_text()
                    print(f"✅ Step 4 - Content verification: {len(content)} characters in {sample_file.name}")
        
        except Exception as e:
            print(f"❌ Real-world usage error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠️  No real data directories found for testing")


def main():
    """Main debug function."""
    print("🐛 API Functionality Debug Tool")
    print("=" * 50)
    
    # Test basic initialization
    test_basic_initialization()
    
    # Test symbol detection API
    test_symbol_detection_api()
    
    # Test data processing API
    test_data_processing_api()
    
    # Test error handling
    test_error_handling_api()
    
    # Test real-world scenarios
    test_real_world_usage()
    
    print(f"\n✅ API debug session completed!")


if __name__ == "__main__":
    main()
