"""
Tests for the HARExtractor class.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from stockreports.extractors import HARExtractor


class TestHARExtractor:
    """Test cases for HARExtractor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.source_dir = Path(self.temp_dir) / "source"
        self.output_dir = Path(self.temp_dir) / "output"
        self.source_dir.mkdir()
        self.output_dir.mkdir()
        
    def test_init(self):
        """Test HARExtractor initialization."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        
        assert extractor.har_dir == self.source_dir
        assert extractor.output_dir == self.output_dir
        assert extractor.timezone_name == "Asia/Ho_Chi_Minh"
        
    def test_init_with_custom_timezone(self):
        """Test HARExtractor initialization with custom timezone."""
        extractor = HARExtractor(
            str(self.source_dir), 
            str(self.output_dir), 
            tz_name="UTC"
        )
        
        assert extractor.timezone_name == "UTC"
        
    def test_extract_symbol_from_url(self):
        """Test symbol extraction from URLs."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        
        # Test VN30 extraction
        vn30_url = "https://api.example.com/data?symbol=VN30&period=1m"
        assert extractor.extract_symbol_from_url(vn30_url) == "VN30"
        
        # Test VNINDEX extraction  
        vnindex_url = "https://api.example.com/data?symbol=VNINDEX&period=1d"
        assert extractor.extract_symbol_from_url(vnindex_url) == "VNINDEX"
        
        # Test no match
        no_match_url = "https://api.example.com/data?param=value"
        assert extractor.extract_symbol_from_url(no_match_url) is None
        
    def test_calculate_response_hash(self):
        """Test response hash calculation."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        
        # Test hash calculation with sample data
        test_data = {"t": [1234567890], "o": [100.5], "c": [101.0]}
        hash1 = extractor.calculate_response_hash(test_data)
        hash2 = extractor.calculate_response_hash(test_data)
        
        # Same data should produce same hash
        assert hash1 == hash2
        assert len(hash1) > 0
        
        # Different data should produce different hash
        different_data = {"t": [1234567891], "o": [100.6], "c": [101.1]}
        hash3 = extractor.calculate_response_hash(different_data)
        assert hash1 != hash3
        
    def test_is_duplicate_response(self):
        """Test duplicate response detection."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        
        test_data = {"t": [1234567890], "o": [100.5]}
        
        # First time should not be duplicate
        assert not extractor.is_duplicate_response(test_data)
        
        # Second time should be duplicate
        assert extractor.is_duplicate_response(test_data)
        
    def test_setup_directories(self):
        """Test directory setup."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        extractor.setup_directories()
        
        assert extractor.requests_dir.exists()
        assert extractor.responses_dir.exists()
        
    def test_find_har_files(self):
        """Test finding HAR files in source directory."""
        # Create test HAR files
        (self.source_dir / "test1.har").touch()
        (self.source_dir / "test2.har").touch()
        (self.source_dir / "not_har.txt").touch()
        
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        har_files = extractor.find_har_files()
        
        assert len(har_files) == 2
        assert all(f.suffix == '.har' for f in har_files)
        
    def test_no_har_files(self):
        """Test behavior when no HAR files are found."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        har_files = extractor.find_har_files()
        
        assert len(har_files) == 0
