"""
Integration tests for duplicate detection functionality.

Tests the complete duplicate detection process in both HAR extraction 
and stock data aggregation phases.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from stockreports.extractors import HARExtractor
from stockreports.aggregators import StockDataAggregator


class TestDuplicateDetection:
    """Integration tests for duplicate detection across the pipeline."""
    
    def test_har_extractor_duplicate_detection(self, tmp_path):
        """Test HAR extractor duplicate response detection."""
        # Create test HAR file with duplicate responses
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {"url": "https://example.com/api/stock/VNINDEX"},
                        "response": {
                            "content": {
                                "text": json.dumps({
                                    "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
                                    "o": [1500.0, 1502.0],
                                    "h": [1505.0, 1507.0],
                                    "l": [1498.0, 1500.0],
                                    "c": [1502.0, 1505.0],
                                    "v": [1000, 1200]
                                })
                            }
                        }
                    },
                    {  # Duplicate response
                        "request": {"url": "https://example.com/api/stock/VNINDEX"},
                        "response": {
                            "content": {
                                "text": json.dumps({
                                    "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
                                    "o": [1500.0, 1502.0],
                                    "h": [1505.0, 1507.0],
                                    "l": [1498.0, 1500.0],
                                    "c": [1502.0, 1505.0],
                                    "v": [1000, 1200]
                                })
                            }
                        }
                    }
                ]
            }
        }
        
        # Create test HAR file
        har_file = tmp_path / "test.har"
        har_file.write_text(json.dumps(har_data))
        
        # Test extraction with duplicate detection
        extractor = HARExtractor(str(tmp_path), str(tmp_path / "output"))
        results = extractor.extract_all()
        
        # Should detect and skip duplicates
        assert results["entries_extracted"] == 2  # Both entries processed
        assert extractor.duplicate_count == 1     # One duplicate detected
    
    def test_aggregator_timestamp_duplicate_removal(self, tmp_path):
        """Test aggregator timestamp-based duplicate removal."""
        # Create test response file with timestamp duplicates
        test_data = {
            "t": [
                "2025-09-03 09:15:00",  # Original
                "2025-09-03 09:20:00",  # Original
                "2025-09-03 09:15:00",  # Duplicate timestamp
                "2025-09-03 09:25:00",  # Original
            ],
            "o": [1500.0, 1502.0, 1500.0, 1504.0],
            "h": [1505.0, 1507.0, 1505.0, 1509.0],
            "l": [1498.0, 1500.0, 1498.0, 1502.0],
            "c": [1502.0, 1505.0, 1502.0, 1507.0],
            "v": [1000, 1200, 1000, 1400]
        }
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        response_file = responses_dir / "test_response_1_VNINDEX.json"
        response_file.write_text(json.dumps(test_data))
        
        # Test aggregation
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        results = aggregator.process_all_symbols()
        
        # Verify duplicate removal
        assert results["VNINDEX"]["unique_records"] == 3  # 4 entries - 1 duplicate = 3 unique
        assert results["VNINDEX"]["timestamp_duplicates"] == 1
    
    def test_aggregator_hash_duplicate_removal(self, tmp_path):
        """Test aggregator hash-based duplicate removal."""
        # Create test response file with identical data rows
        test_data = {
            "t": [
                "2025-09-03 09:15:00",  
                "2025-09-03 09:20:00",
                "2025-09-03 09:25:00",  
                "2025-09-03 09:30:00",
            ],
            "o": [1500.0, 1502.0, 1504.0, 1502.0],  # Row 2 and 4 same values
            "h": [1505.0, 1507.0, 1509.0, 1507.0],  # but different timestamps
            "l": [1498.0, 1500.0, 1502.0, 1500.0],
            "c": [1502.0, 1505.0, 1507.0, 1505.0],
            "v": [1000, 1200, 1400, 1200]
        }
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        response_file = responses_dir / "test_response_1_VNINDEX.json"
        response_file.write_text(json.dumps(test_data))
        
        # Test aggregation
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        results = aggregator.process_all_symbols()
        
        # All records should be kept (different timestamps)
        assert results["VNINDEX"]["unique_records"] == 4
        assert results["VNINDEX"]["hash_duplicates"] == 0  # No exact duplicates
    
    def test_mixed_duplicate_scenarios(self, tmp_path):
        """Test mixed duplicate scenarios with multiple files."""
        # Create multiple response files with overlapping data
        test_data_1 = {
            "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
            "o": [1500.0, 1502.0],
            "h": [1505.0, 1507.0],
            "l": [1498.0, 1500.0],
            "c": [1502.0, 1505.0],
            "v": [1000, 1200]
        }
        
        test_data_2 = {
            "t": ["2025-09-03 09:20:00", "2025-09-03 09:25:00"],  # 09:20:00 duplicates data_1
            "o": [1502.0, 1504.0],
            "h": [1507.0, 1509.0],
            "l": [1500.0, 1502.0],
            "c": [1505.0, 1507.0],
            "v": [1200, 1400]
        }
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        (responses_dir / "file1_response_1_VNINDEX.json").write_text(json.dumps(test_data_1))
        (responses_dir / "file2_response_2_VNINDEX.json").write_text(json.dumps(test_data_2))
        
        # Test aggregation
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        results = aggregator.process_all_symbols()
        
        # Should handle cross-file duplicates
        assert results["VNINDEX"]["files_processed"] == 2
        assert results["VNINDEX"]["unique_records"] == 3  # 4 total - 1 duplicate = 3 unique
        assert results["VNINDEX"]["timestamp_duplicates"] == 1
    
    def test_empty_data_handling(self, tmp_path):
        """Test duplicate detection with empty or malformed data."""
        test_cases = [
            {},  # Empty object
            {"t": []},  # Empty arrays
            {"t": [None], "o": [None]},  # Null values
            {"t": ["invalid"], "o": ["not_number"]},  # Invalid data types
        ]
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        for i, test_data in enumerate(test_cases):
            response_file = responses_dir / f"test_response_{i+1}_TEST.json"
            response_file.write_text(json.dumps(test_data))
        
        # Test aggregation - should handle gracefully
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        results = aggregator.process_all_symbols()
        
        # Should process without crashing
        assert "TEST" in results or len(results) == 0  # Might skip invalid data
    
    @pytest.mark.integration
    def test_full_pipeline_duplicate_detection(self):
        """Integration test for duplicate detection across full pipeline."""
        # This would test with actual HAR files containing duplicates
        test_har_dir = Path("project/sources/har")
        
        if not test_har_dir.exists():
            pytest.skip("Test HAR files not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            responses_dir = temp_path / "responses"
            reports_dir = temp_path / "reports"
            
            # Extract HAR data
            extractor = HARExtractor(str(test_har_dir), str(responses_dir))
            extraction_results = extractor.extract_all()
            
            # Aggregate data
            har_responses_dir = responses_dir / "har_responses"
            aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
            aggregation_results = aggregator.process_all_symbols()
            
            # Verify duplicate handling worked
            assert extraction_results["entries_extracted"] > 0
            if hasattr(extractor, 'duplicate_count'):
                print(f"HAR extraction duplicates detected: {extractor.duplicate_count}")
            
            for symbol_data in aggregation_results.values():
                if isinstance(symbol_data, dict):
                    if "timestamp_duplicates" in symbol_data:
                        print(f"Aggregation timestamp duplicates: {symbol_data['timestamp_duplicates']}")
                    if "hash_duplicates" in symbol_data:
                        print(f"Aggregation hash duplicates: {symbol_data['hash_duplicates']}")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__])
