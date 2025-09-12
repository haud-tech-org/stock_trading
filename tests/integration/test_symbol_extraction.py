"""
Integration tests for symbol extraction functionality.

Tests the complete symbol discovery and extraction process from HAR response files.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import patch, MagicMock

from stockreports.aggregators import StockDataAggregator


class TestSymbolExtraction:
    """Integration tests for symbol extraction from response files."""
    
    def test_symbol_extraction_regex_pattern(self, tmp_path):
        """Test symbol extraction regex pattern with various filename formats."""
        test_cases = [
            ("all-25-11-09_response_1_VNINDEX.json", "VNINDEX"),
            ("VN30-1m_response_85_VNINDEX.json", "VNINDEX"),
            ("test_response_42_VN30.json", "VN30"),
            ("response_1_HPG.json", "HPG"),
            ("data_response_999_VCB.json", "VCB"),
            ("sample_response_5_VIC.json", "VIC"),
            ("export_response_12_VPB.json", "VPB"),
        ]
        
        pattern = r'response_\d+_([^.]+)\.json$'
        
        for filename, expected_symbol in test_cases:
            match = re.search(pattern, filename)
            assert match is not None, f"Pattern should match filename: {filename}"
            extracted_symbol = match.group(1)
            assert extracted_symbol == expected_symbol, (
                f"Expected symbol '{expected_symbol}', got '{extracted_symbol}' "
                f"from filename '{filename}'"
            )
    
    def test_symbol_extraction_invalid_patterns(self):
        """Test that invalid filename patterns don't match."""
        invalid_cases = [
            "not_a_response_file.json",
            "response_VNINDEX.json",  # Missing number
            "response_1_VNINDEX.txt",  # Wrong extension
            "response_abc_VNINDEX.json",  # Non-numeric index
            "prefix_response_1_.json",  # Missing symbol
        ]
        
        pattern = r'response_\d+_([^.]+)\.json$'
        
        for filename in invalid_cases:
            match = re.search(pattern, filename)
            assert match is None, f"Pattern should NOT match invalid filename: {filename}"
    
    def test_aggregator_symbol_discovery(self, tmp_path):
        """Test StockDataAggregator symbol discovery from actual files."""
        # Create test response files
        test_files = [
            "sample_response_1_VNINDEX.json",
            "sample_response_2_VN30.json", 
            "sample_response_3_HPG.json",
            "sample_response_4_VCB.json",
            "sample_response_5_VIC.json",
            "sample_response_6_VPB.json",
            "not_a_response.json",  # Should be ignored
            "response_invalid.txt",  # Should be ignored
        ]
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        # Create empty files
        for filename in test_files:
            (responses_dir / filename).write_text("{}")
        
        # Test symbol extraction
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        symbols = aggregator.extract_symbols_from_files()
        
        expected_symbols = ["HPG", "VCB", "VIC", "VN30", "VNINDEX", "VPB"]
        assert sorted(symbols) == sorted(expected_symbols), (
            f"Expected symbols {expected_symbols}, got {symbols}"
        )
    
    def test_symbol_extraction_empty_directory(self, tmp_path):
        """Test symbol extraction from empty directory."""
        empty_dir = tmp_path / "empty_responses"
        empty_dir.mkdir()
        
        aggregator = StockDataAggregator(str(empty_dir), str(tmp_path / "output"))
        symbols = aggregator.extract_symbols_from_files()
        
        assert symbols == [], "Empty directory should return no symbols"
    
    def test_symbol_extraction_no_response_files(self, tmp_path):
        """Test symbol extraction when no response files exist."""
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        # Create non-response files
        (responses_dir / "data.json").write_text("{}")
        (responses_dir / "config.json").write_text("{}")
        (responses_dir / "readme.txt").write_text("info")
        
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        symbols = aggregator.extract_symbols_from_files()
        
        assert symbols == [], "Directory with no response files should return no symbols"
    
    def test_symbol_extraction_duplicate_symbols(self, tmp_path):
        """Test that duplicate symbols are handled correctly."""
        test_files = [
            "har1_response_1_VNINDEX.json",
            "har1_response_2_VNINDEX.json",  # Duplicate symbol
            "har2_response_3_VN30.json",
            "har2_response_4_VN30.json",     # Duplicate symbol
            "har3_response_5_HPG.json",
        ]
        
        responses_dir = tmp_path / "responses"
        responses_dir.mkdir()
        
        for filename in test_files:
            (responses_dir / filename).write_text("{}")
        
        aggregator = StockDataAggregator(str(responses_dir), str(tmp_path / "output"))
        symbols = aggregator.extract_symbols_from_files()
        
        # Should return unique symbols only
        expected_symbols = ["HPG", "VN30", "VNINDEX"]
        assert sorted(symbols) == sorted(expected_symbols), (
            f"Expected unique symbols {expected_symbols}, got {symbols}"
        )
    
    @pytest.mark.integration
    def test_symbol_extraction_integration_with_real_data(self):
        """Integration test with real-world data if available."""
        # This test would use actual HAR response files if they exist
        test_data_dir = Path("final_validation_reports/responses/har_responses")
        
        if not test_data_dir.exists():
            pytest.skip("Real test data not available")
        
        aggregator = StockDataAggregator(str(test_data_dir), "test_output")
        symbols = aggregator.extract_symbols_from_files()
        
        # Verify we get reasonable symbols for Vietnamese stock market
        assert len(symbols) > 0, "Should find at least one symbol"
        assert all(isinstance(symbol, str) and len(symbol) > 0 for symbol in symbols), (
            "All symbols should be non-empty strings"
        )
        
        # Common Vietnamese stock symbols should be uppercase
        assert all(symbol.isupper() for symbol in symbols), (
            "Stock symbols should be uppercase"
        )


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__])
