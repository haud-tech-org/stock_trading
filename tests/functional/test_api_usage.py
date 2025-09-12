"""
Functional tests for the stockreports public API.

Tests the public API interface, usability, and expected behaviors
that end users will interact with.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from stockreports import HARExtractor, StockDataAggregator


class TestPublicAPI:
    """Functional tests for public API interface."""
    
    def test_har_extractor_initialization(self):
        """Test HARExtractor can be initialized with various parameters."""
        # Test with minimal parameters
        extractor = HARExtractor("test_dir")
        assert extractor.har_dir == Path("test_dir")
        
        # Test with output directory
        extractor = HARExtractor("test_dir", "output_dir")
        assert extractor.output_dir == Path("output_dir")
        
        # Test with timezone parameter
        extractor = HARExtractor("test_dir", "output_dir", tz_name="Asia/Ho_Chi_Minh")
        assert extractor.timezone_name == "Asia/Ho_Chi_Minh"
    
    def test_stock_aggregator_initialization(self):
        """Test StockDataAggregator can be initialized properly."""
        aggregator = StockDataAggregator("responses_dir", "output_dir")
        assert aggregator.responses_dir == Path("responses_dir")
        assert aggregator.output_dir == Path("output_dir")
    
    def test_aggregator_symbol_detection_api(self, tmp_path):
        """Test the symbol detection API works correctly."""
        # Create test response files
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        test_files = [
            ("test_response_1_VNINDEX.json", {}),
            ("test_response_2_VN30.json", {}),
            ("test_response_3_HPG.json", {}),
        ]
        
        for filename, content in test_files:
            (responses_dir / filename).write_text(json.dumps(content))
        
        # Test API
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        symbols = aggregator.extract_symbols_from_files()
        
        assert isinstance(symbols, list), "extract_symbols_from_files should return a list"
        assert len(symbols) == 3, "Should find 3 symbols"
        assert set(symbols) == {"VNINDEX", "VN30", "HPG"}, "Should extract correct symbols"
    
    def test_aggregator_data_processing_api(self, tmp_path):
        """Test the data processing API works correctly."""
        # Create test response file with valid data
        test_data = {
            "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
            "o": [1500.0, 1502.0],
            "h": [1505.0, 1507.0],
            "l": [1498.0, 1500.0],
            "c": [1502.0, 1505.0],
            "v": [1000, 1200]
        }
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        (responses_dir / "test_response_1_VNINDEX.json").write_text(json.dumps(test_data))
        
        # Test API
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        
        # Test individual symbol processing
        symbol_data, files_count, detected_columns = aggregator.aggregate_symbol_data("VNINDEX")
        
        assert isinstance(symbol_data, list), "aggregate_symbol_data should return list of data"
        assert len(symbol_data) == 2, "Should process 2 data points"
        assert files_count == 1, "Should process 1 file"
        assert isinstance(detected_columns, dict), "Should return detected columns dict"
        assert "t" in detected_columns, "Should detect timestamp column"
    
    def test_full_processing_pipeline_api(self, tmp_path):
        """Test the complete processing pipeline API."""
        # Create test response files
        test_data = {
            "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
            "o": [1500.0, 1502.0],
            "h": [1505.0, 1507.0],
            "l": [1498.0, 1500.0],
            "c": [1502.0, 1505.0],
            "v": [1000, 1200]
        }
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        (responses_dir / "test_response_1_VNINDEX.json").write_text(json.dumps(test_data))
        
        # Test full pipeline
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        results = aggregator.process_all_symbols()
        
        # Verify API response structure
        assert isinstance(results, dict), "process_all_symbols should return dict"
        assert "VNINDEX" in results, "Should process VNINDEX symbol"
        
        symbol_result = results["VNINDEX"]
        assert isinstance(symbol_result, dict), "Symbol result should be dict"
        
        # Check expected result structure
        expected_keys = ["total_files", "unique_records", "trading_days"]
        for key in expected_keys:
            assert key in symbol_result, f"Result should contain '{key}' key"
    
    def test_api_error_handling(self, tmp_path):
        """Test API error handling for common failure cases."""
        # Test with non-existent directory
        aggregator = StockDataAggregator("nonexistent_dir", str(tmp_path / "output"))
        
        # Should handle gracefully
        symbols = aggregator.extract_symbols_from_files()
        assert symbols == [], "Should return empty list for non-existent directory"
        
        # Test with empty directory
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        aggregator = StockDataAggregator(str(empty_dir), str(tmp_path / "output"))
        symbols = aggregator.extract_symbols_from_files()
        assert symbols == [], "Should return empty list for empty directory"
    
    def test_api_data_validation(self, tmp_path):
        """Test API handles invalid data gracefully."""
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        # Test with invalid JSON
        (responses_dir / "test_response_1_INVALID.json").write_text("invalid json")
        
        # Test with empty JSON
        (responses_dir / "test_response_2_EMPTY.json").write_text("{}")
        
        # Test with malformed data structure
        (responses_dir / "test_response_3_MALFORMED.json").write_text(
            json.dumps({"wrong": "structure"})
        )
        
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        
        # Should not crash
        symbols = aggregator.extract_symbols_from_files()
        assert len(symbols) == 3, "Should find symbols from filenames even with invalid data"
        
        # Processing should handle errors gracefully
        results = aggregator.process_all_symbols()
        assert isinstance(results, dict), "Should return dict even with invalid data"
    
    @pytest.mark.integration
    def test_real_world_api_usage(self):
        """Test API with real-world usage patterns."""
        # Test the common usage pattern shown in documentation
        responses_dir = Path("final_validation_reports/responses/har_responses")
        
        if not responses_dir.exists():
            pytest.skip("Real test data not available")
        
        # Test typical user workflow
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Initialize aggregator
            aggregator = StockDataAggregator(str(responses_dir), temp_dir)
            
            # 2. Discover symbols
            symbols = aggregator.extract_symbols_from_files()
            assert len(symbols) > 0, "Should find symbols in real data"
            
            # 3. Process all symbols
            results = aggregator.process_all_symbols()
            assert len(results) > 0, "Should process symbols successfully"
            
            # 4. Verify output files were created
            output_dir = Path(temp_dir)
            report_files = list(output_dir.glob("*.md"))
            assert len(report_files) > 0, "Should generate report files"
            
            # 5. Verify report content structure
            for report_file in report_files[:2]:  # Check first 2 files
                content = report_file.read_text()
                assert len(content) > 100, f"Report {report_file.name} should have substantial content"
                assert "# " in content, f"Report {report_file.name} should have markdown headers"
    
    def test_api_backwards_compatibility(self, tmp_path):
        """Test that API maintains backwards compatibility."""
        # Test that old method names/signatures still work
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        test_data = {"t": ["2025-09-03 09:15:00"], "o": [1500.0]}
        (responses_dir / "test_response_1_TEST.json").write_text(json.dumps(test_data))
        
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        
        # Test method availability
        assert hasattr(aggregator, "extract_symbols_from_files"), "Should have symbol extraction method"
        assert hasattr(aggregator, "process_all_symbols"), "Should have processing method"
        assert hasattr(aggregator, "aggregate_symbol_data"), "Should have individual symbol method"
        
        # Test methods are callable
        assert callable(aggregator.extract_symbols_from_files), "Symbol extraction should be callable"
        assert callable(aggregator.process_all_symbols), "Processing should be callable"
        assert callable(aggregator.aggregate_symbol_data), "Individual processing should be callable"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__])
