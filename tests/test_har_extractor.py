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
        
        assert extractor.source_dir == self.source_dir
        assert extractor.output_dir == self.output_dir
        assert extractor.timezone == "Asia/Ho_Chi_Minh"
        
    def test_init_with_custom_timezone(self):
        """Test HARExtractor initialization with custom timezone."""
        extractor = HARExtractor(
            str(self.source_dir), 
            str(self.output_dir), 
            timezone="UTC"
        )
        
        assert extractor.timezone == "UTC"
        
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
        
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_process_har_entry_valid(self, mock_json_load, mock_file):
        """Test processing a valid HAR entry."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        
        # Mock HAR entry
        entry = {
            'request': {'url': 'https://api.example.com/data?symbol=VN30'},
            'response': {'content': {'text': '{"t":[1234567890],"o":[100.5]}'}}
        }
        
        # Mock JSON response
        mock_response = {"t": [1234567890], "o": [100.5]}
        mock_json_load.return_value = mock_response
        
        result = extractor.process_har_entry(entry, "test_source", 1)
        
        assert result is not None
        assert result['symbol'] == 'VN30'
        assert result['index'] == 1
        
    def test_process_har_entry_no_symbol(self):
        """Test processing HAR entry with no symbol match."""
        extractor = HARExtractor(str(self.source_dir), str(self.output_dir))
        
        entry = {
            'request': {'url': 'https://api.example.com/data?param=value'},
            'response': {'content': {'text': '{"data": "test"}'}}
        }
        
        result = extractor.process_har_entry(entry, "test_source", 1)
        assert result is None
        
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
