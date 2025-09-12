"""
Tests for the StockDataAggregator class.
"""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch, mock_open

from stockreports.aggregators import StockDataAggregator


class TestStockDataAggregator:
    """Test cases for StockDataAggregator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.responses_dir = Path(self.temp_dir) / "responses"
        self.output_dir = Path(self.temp_dir) / "output"
        self.responses_dir.mkdir()
        self.output_dir.mkdir()
        
    def test_init(self):
        """Test StockDataAggregator initialization."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        
        assert aggregator.responses_dir == self.responses_dir
        assert aggregator.output_dir == self.output_dir
        assert aggregator.output_dir.exists()
        
    def test_extract_symbols_from_files(self):
        """Test extracting symbols from response filenames."""
        # Create test response files
        (self.responses_dir / "source1_response_1_VN30.json").touch()
        (self.responses_dir / "source1_response_2_VNINDEX.json").touch()
        (self.responses_dir / "source2_response_3_VN30.json").touch()
        (self.responses_dir / "not_response.json").touch()
        
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        symbols = aggregator.extract_symbols_from_files()
        
        assert sorted(symbols) == ['VN30', 'VNINDEX']
        
    def test_detect_data_columns(self):
        """Test detecting columns from sample data."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        
        sample_data = {
            't': [1234567890, 1234567891],
            'o': [100.5, 101.0],
            'h': [102.0, 103.0],
            'l': [99.0, 100.0],
            'c': [101.5, 102.5],
            'v': [10000, 15000]
        }
        
        columns = aggregator.detect_data_columns(sample_data)
        
        expected_keys = {'t', 'o', 'h', 'l', 'c', 'v'}
        assert set(columns.keys()) == expected_keys
        
    def test_detect_data_columns_empty(self):
        """Test detecting columns from empty data."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        
        columns = aggregator.detect_data_columns({})
        assert columns == {}
        
    def test_calculate_symbol_statistics(self):
        """Test calculating statistics for symbol data."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        
        # Mock data with ordered columns (t, o, h, l, c, v)
        data = [
            (('2023-01-01 09:00:00', 100.0, 102.0, 99.0, 101.0, 10000), {}),
            (('2023-01-01 09:01:00', 101.0, 103.0, 100.0, 102.0, 15000), {}),
        ]
        
        columns = {
            't': 'Date Time',
            'o': 'Open',
            'h': 'High', 
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume'
        }
        
        stats = aggregator.calculate_symbol_statistics(data, columns)
        
        assert stats['total_records'] == 2
        assert 'date_range' in stats
        assert 'price_range' in stats
        assert 'volume' in stats
        
    def test_calculate_statistics_empty_data(self):
        """Test calculating statistics with empty data."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        
        stats = aggregator.calculate_symbol_statistics([], {})
        assert stats == {}
        
    @patch('builtins.open', new_callable=mock_open)
    def test_generate_symbol_summary(self, mock_file):
        """Test generating symbol summary report."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        
        data = [
            (('2023-01-01 09:00:00', 100.0, 102.0, 99.0, 101.0, 10000), {}),
        ]
        
        columns = {
            't': 'Date Time',
            'o': 'Open',
            'h': 'High',
            'l': 'Low', 
            'c': 'Close',
            'v': 'Volume'
        }
        
        stats = {'total_records': 1}
        
        result_path = aggregator.generate_symbol_summary('VN30', data, stats, columns)
        
        assert 'vn30_summary.md' in result_path
        mock_file.assert_called_once()
        
    def test_no_response_files(self):
        """Test behavior when no response files are found."""
        aggregator = StockDataAggregator(str(self.responses_dir), str(self.output_dir))
        symbols = aggregator.extract_symbols_from_files()
        
        assert symbols == []
