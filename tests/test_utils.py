"""Tests for the utils module."""

from stockreports.utils.data_utils import (
    STANDARD_COLUMN_MAP,
    TRADING_HOURS,
    VIETNAM_TIMEZONE,
    TIME_FORMATS,
    get_available_columns,
    get_ordered_columns,
    validate_data_structure,
    is_trading_hours,
    get_trading_hours_info,
    get_vietnam_timezone_offset
)


class TestDataUtils:
    """Test cases for data utilities."""
    
    def test_standard_column_map(self):
        """Test that standard column map contains expected mappings."""
        expected_keys = {'t', 'o', 'h', 'l', 'c', 'v'}
        assert set(STANDARD_COLUMN_MAP.keys()) == expected_keys
        
    def test_get_available_columns(self):
        """Test getting available columns from data sample."""
        data_sample = {
            't': [1234567890, 1234567891],
            'o': [100.0, 101.0], 
            'h': [102.0, 103.0],
            'invalid': "not a list"
        }
        
        columns = get_available_columns(data_sample)
        
        # Should only return columns that are lists and in our mapping
        expected = {'t': 'Date Time', 'o': 'Open', 'h': 'High'}
        assert columns == expected
        
    def test_get_available_columns_empty(self):
        """Test getting columns from empty data."""
        assert get_available_columns({}) == {}
        assert get_available_columns(None) == {}
        
    def test_get_ordered_columns(self):
        """Test getting columns in preferred order."""
        columns = {
            'v': 'Volume',
            't': 'Date Time', 
            'c': 'Close',
            'o': 'Open'
        }
        
        ordered = get_ordered_columns(columns)
        
        # Should start with preferred order where available
        assert ordered[0] == 't'  # First in preferred order
        assert ordered[1] == 'o'  # Second in preferred order
        assert 'c' in ordered
        assert 'v' in ordered
        
    def test_validate_data_structure_valid(self):
        """Test validating a valid data structure."""
        valid_data = {
            't': [1234567890],
            'o': [100.0],
            'c': [101.0]
        }
        
        is_valid, message = validate_data_structure(valid_data)
        
        assert is_valid is True
        assert "valid" in message.lower()
        
    def test_validate_data_structure_invalid(self):
        """Test validating invalid data structures."""
        # Not a dictionary
        is_valid, message = validate_data_structure("not a dict")
        assert is_valid is False
        assert "dictionary" in message.lower()
        
        # No standard columns
        invalid_data = {'unknown': [1, 2, 3]}
        is_valid, message = validate_data_structure(invalid_data)
        assert is_valid is False
        assert "standard columns" in message.lower()
        
        # Column not a list
        invalid_data = {'t': "not a list"}
        is_valid, message = validate_data_structure(invalid_data)
        assert is_valid is False
        assert "list data" in message.lower()
    
    def test_trading_hours_constants(self):
        """Test that trading hours constants are correctly defined."""
        assert TRADING_HOURS['start_hour'] == 9
        assert TRADING_HOURS['start_minute'] == 0
        assert TRADING_HOURS['end_hour'] == 14
        assert TRADING_HOURS['end_minute'] == 45
        assert TRADING_HOURS['start_minutes'] == 540  # 9 * 60
        assert TRADING_HOURS['end_minutes'] == 885    # 14 * 60 + 45
    
    def test_vietnam_timezone_constants(self):
        """Test that Vietnam timezone constants are correctly defined."""
        assert VIETNAM_TIMEZONE['offset_hours'] == 7
        assert VIETNAM_TIMEZONE['name'] == 'Asia/Ho_Chi_Minh'
        assert VIETNAM_TIMEZONE['display_name'] == 'Vietnam Time'
    
    def test_time_formats_constants(self):
        """Test that time format constants are correctly defined."""
        assert TIME_FORMATS['datetime_display'] == '%Y-%m-%d %H:%M:%S'
        assert TIME_FORMATS['date_only'] == '%Y-%m-%d'
        assert TIME_FORMATS['time_only'] == '%H:%M:%S'
        assert TIME_FORMATS['filename_timestamp'] == '%Y-%m-%d-%H-%M-%S'
    
    def test_is_trading_hours(self):
        """Test trading hours checking function."""
        # Within trading hours
        assert is_trading_hours(9, 0) == True    # 09:00
        assert is_trading_hours(12, 30) == True  # 12:30
        assert is_trading_hours(14, 45) == True  # 14:45 (end)
        
        # Outside trading hours
        assert is_trading_hours(8, 59) == False  # Before start
        assert is_trading_hours(14, 46) == False # After end
        assert is_trading_hours(15, 0) == False  # Afternoon
        assert is_trading_hours(0, 0) == False   # Midnight
    
    def test_get_trading_hours_info(self):
        """Test trading hours info function."""
        info = get_trading_hours_info()
        
        assert info['start_time'] == '09:00'
        assert info['end_time'] == '14:45'
        assert info['display_range'] == '09:00 - 14:45'
        assert 'Trading hours (09:00 - 14:45 Vietnam Time)' in info['description']
    
    def test_get_vietnam_timezone_offset(self):
        """Test Vietnam timezone offset function."""
        offset = get_vietnam_timezone_offset()
        assert offset == 7
