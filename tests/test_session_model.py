"""
Tests for the Session model and its conversion methods.

Demonstrates how to use the centralized Session model with various
data formats and sources.
"""

import pytest
from src.stockreports.model import Session


class TestSessionCreation:
    """Test basic Session object creation and validation."""
    
    def test_create_session_directly(self):
        """Test creating a Session object directly."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_session_immutability(self):
        """Test that Session objects are immutable (frozen dataclass)."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        
        with pytest.raises(AttributeError):
            session.name = "afternoon"
    
    def test_invalid_start_time_format(self):
        """Test that invalid start time format raises ValueError."""
        with pytest.raises(ValueError, match="Start time must be HH:MM format"):
            Session(name="morning", start_time="300", end_time="12:00")
    
    def test_invalid_end_time_format(self):
        """Test that invalid end time format raises ValueError."""
        with pytest.raises(ValueError, match="End time must be HH:MM format"):
            Session(name="morning", start_time="03:00", end_time="12")
    
    def test_invalid_hour_in_time(self):
        """Test that hours outside 0-23 range raise ValueError."""
        with pytest.raises(ValueError, match="Invalid.*time"):
            Session(name="morning", start_time="25:00", end_time="12:00")
    
    def test_invalid_minute_in_time(self):
        """Test that minutes outside 0-59 range raise ValueError."""
        with pytest.raises(ValueError, match="Invalid.*time"):
            Session(name="morning", start_time="03:00", end_time="12:75")


class TestSessionConversions:
    """Test conversion methods of Session."""
    
    def test_to_dict(self):
        """Test conversion to dict format with 'start' and 'end' keys."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        result = session.to_dict()
        
        assert result == {"start": "03:00", "end": "12:00"}
    
    def test_to_tuple(self):
        """Test conversion to tuple format."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        result = session.to_tuple()
        
        assert result == ("morning", "03:00", "12:00")
    
    def test_to_sessions_dict_entry(self):
        """Test conversion to SESSIONS dict entry format."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        name, times = session.to_sessions_dict_entry()
        
        assert name == "morning"
        assert times == {"start": "03:00", "end": "12:00"}


class TestSessionFromDict:
    """Test Session.from_dict() conversion method."""
    
    def test_from_dict_standard_format(self):
        """Test conversion from dict with standard keys."""
        data = {
            "name": "morning",
            "start_time": "03:00",
            "end_time": "12:00"
        }
        session = Session.from_dict(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_dict_alternate_format(self):
        """Test conversion from dict with alternate 'start'/'end' keys."""
        data = {
            "name": "morning",
            "start": "03:00",
            "end": "12:00"
        }
        session = Session.from_dict(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_dict_missing_name(self):
        """Test that missing 'name' key raises ValueError."""
        data = {"start_time": "03:00", "end_time": "12:00"}
        
        with pytest.raises(ValueError, match="Missing required key: 'name'"):
            Session.from_dict(data)
    
    def test_from_dict_missing_start(self):
        """Test that missing start time key raises ValueError."""
        data = {"name": "morning", "end_time": "12:00"}
        
        with pytest.raises(ValueError, match="Missing required key"):
            Session.from_dict(data)
    
    def test_from_dict_not_dict(self):
        """Test that non-dict input raises TypeError."""
        with pytest.raises(TypeError, match="Expected dict"):
            Session.from_dict("not a dict")


class TestSessionFromTuple:
    """Test Session.from_tuple() conversion method."""
    
    def test_from_tuple(self):
        """Test conversion from tuple format."""
        data = ("morning", "03:00", "12:00")
        session = Session.from_tuple(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_list(self):
        """Test conversion from list format."""
        data = ["morning", "03:00", "12:00"]
        session = Session.from_tuple(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_tuple_wrong_length(self):
        """Test that tuple with wrong length raises ValueError."""
        data = ("morning", "03:00")
        
        with pytest.raises(ValueError, match="Expected tuple of length 3"):
            Session.from_tuple(data)
    
    def test_from_tuple_not_tuple(self):
        """Test that non-tuple input raises TypeError."""
        with pytest.raises(TypeError, match="Expected tuple or list"):
            Session.from_tuple("not a tuple")


class TestSessionFromSessionsDictEntry:
    """Test Session.from_sessions_dict_entry() conversion method."""
    
    def test_from_sessions_dict_entry(self):
        """Test conversion from SESSIONS dict entry format."""
        session = Session.from_sessions_dict_entry(
            "morning",
            {"start": "03:00", "end": "12:00"}
        )
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_sessions_dict_entry_missing_start(self):
        """Test that missing 'start' in times dict raises ValueError."""
        with pytest.raises(ValueError, match="Missing 'start'"):
            Session.from_sessions_dict_entry("morning", {"end": "12:00"})
    
    def test_from_sessions_dict_entry_missing_end(self):
        """Test that missing 'end' in times dict raises ValueError."""
        with pytest.raises(ValueError, match="Missing 'end'"):
            Session.from_sessions_dict_entry("morning", {"start": "03:00"})
    
    def test_from_sessions_dict_entry_not_dict(self):
        """Test that non-dict times raises TypeError."""
        with pytest.raises(TypeError, match="Expected dict for times"):
            Session.from_sessions_dict_entry("morning", "not a dict")


class TestSessionFromTradeSessionConfig:
    """Test Session.from_trade_session_config() conversion method."""
    
    def test_from_trade_session_config(self):
        """Test conversion from TradeSessionConfig object."""
        # Create a mock TradeSessionConfig-like object
        class MockTradeSessionConfig:
            def __init__(self):
                self.name = "morning"
                self.start_time = "03:00"
                self.end_time = "12:00"
        
        trade_config = MockTradeSessionConfig()
        session = Session.from_trade_session_config(trade_config)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_trade_session_config_missing_attribute(self):
        """Test that missing attributes raise TypeError."""
        class IncompleteConfig:
            def __init__(self):
                self.name = "morning"
                # missing start_time and end_time
        
        config = IncompleteConfig()
        
        with pytest.raises(TypeError, match="does not have TradeSessionConfig structure"):
            Session.from_trade_session_config(config)


class TestSessionFromAny:
    """Test Session.from_any() smart conversion method."""
    
    def test_from_any_session_object(self):
        """Test that Session objects are returned as-is."""
        original = Session(name="morning", start_time="03:00", end_time="12:00")
        result = Session.from_any(original)
        
        assert result is original
    
    def test_from_any_dict(self):
        """Test smart conversion from dict."""
        data = {
            "name": "morning",
            "start_time": "03:00",
            "end_time": "12:00"
        }
        session = Session.from_any(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_any_tuple(self):
        """Test smart conversion from tuple."""
        data = ("morning", "03:00", "12:00")
        session = Session.from_any(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_any_list(self):
        """Test smart conversion from list."""
        data = ["morning", "03:00", "12:00"]
        session = Session.from_any(data)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_any_trade_config(self):
        """Test smart conversion from TradeSessionConfig-like object."""
        class MockTradeSessionConfig:
            def __init__(self):
                self.name = "morning"
                self.start_time = "03:00"
                self.end_time = "12:00"
        
        config = MockTradeSessionConfig()
        session = Session.from_any(config)
        
        assert session.name == "morning"
        assert session.start_time == "03:00"
        assert session.end_time == "12:00"
    
    def test_from_any_sessions_dict_entry_fails(self):
        """Test that bare SESSIONS dict entry (only start/end) fails."""
        data = {"start": "03:00", "end": "12:00"}
        
        with pytest.raises(ValueError, match="Cannot convert dict with only"):
            Session.from_any(data)
    
    def test_from_any_unsupported_type(self):
        """Test that unsupported types raise TypeError."""
        with pytest.raises(TypeError, match="Cannot convert"):
            Session.from_any(12345)


class TestSessionStringRepresentations:
    """Test string representation methods."""
    
    def test_str_representation(self):
        """Test __str__ method."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        assert str(session) == "morning (03:00-12:00)"
    
    def test_repr_representation(self):
        """Test __repr__ method."""
        session = Session(name="morning", start_time="03:00", end_time="12:00")
        expected = "Session(name='morning', start_time='03:00', end_time='12:00')"
        assert repr(session) == expected


class TestSessionIntegration:
    """Integration tests showing real-world usage patterns."""
    
    def test_sessions_list_conversion(self):
        """Test converting a list of sessions from various formats."""
        sessions_data = [
            ("morning", "03:00", "12:00"),
            {"name": "afternoon", "start": "12:10", "end": "22:30"},
            Session(name="night", start_time="22:30", end_time="02:59"),
        ]
        
        sessions = [Session.from_any(data) for data in sessions_data]
        
        assert len(sessions) == 3
        assert sessions[0].name == "morning"
        assert sessions[1].name == "afternoon"
        assert sessions[2].name == "night"
    
    def test_sessions_dict_building(self):
        """Test building a SESSIONS dictionary from multiple sources."""
        sessions_data = [
            ("morning", "03:00", "12:00"),
            {"name": "afternoon", "start": "12:10", "end": "22:30"},
        ]
        
        sessions = [Session.from_any(data) for data in sessions_data]
        sessions_dict = {
            name: times
            for name, times in [s.to_sessions_dict_entry() for s in sessions]
        }
        
        expected = {
            "morning": {"start": "03:00", "end": "12:00"},
            "afternoon": {"start": "12:10", "end": "22:30"}
        }
        
        assert sessions_dict == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
