import pytest
import pandas as pd
from unittest.mock import patch

# It's good practice to set up the path for test discovery
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.stockreports.alert.price_movement_alerter import PriceMovementAlerter

# Mock settings that will be returned by the mocked loader
MOCK_PRICE_ALERT_SETTINGS = {
    "ALLOW_REPEATED_LEVEL_ALERTS": False,
    "PRICE_ALERTS": {
        "TEST_SYMBOL": {
            "reference_price": 100.0,
            "fixed_levels": [105.0, 110.0],
            "absolute_interval": 10.0,
        },
    }
}

@pytest.fixture
def mock_settings():
    """Fixture to mock the price alert settings loader."""
    with patch('src.stockreports.alert.price_movement_alerter.get_price_alert_settings') as mock_getter:
        # Create a simple object that mimics the settings module
        class MockSettingsModule:
            ALLOW_REPEATED_LEVEL_ALERTS = MOCK_PRICE_ALERT_SETTINGS["ALLOW_REPEATED_LEVEL_ALERTS"]
            PRICE_ALERTS = MOCK_PRICE_ALERT_SETTINGS["PRICE_ALERTS"]
        
        mock_getter.return_value = MockSettingsModule
        yield mock_getter

def test_fixed_level_crossing_up(mock_settings):
    """Test when price crosses a fixed level upwards."""
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [104.9, 105.1]
    })
    alerter = PriceMovementAlerter("TEST_SYMBOL", set())
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 1
    assert "'TEST_SYMBOL' crossed above fixed price level of 105.00" in alerts[0]

def test_fixed_level_crossing_down(mock_settings):
    """Test when price crosses a fixed level downwards."""
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [105.1, 104.9]
    })
    alerter = PriceMovementAlerter("TEST_SYMBOL", set())
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 1
    assert "'TEST_SYMBOL' crossed below fixed price level of 105.00" in alerts[0]

def test_no_crossing(mock_settings):
    """Test when price moves but does not cross a level."""
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [104.1, 104.5]
    })
    alerter = PriceMovementAlerter("TEST_SYMBOL", set())
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 0

def test_interval_crossing_up(mock_settings):
    """Test when price crosses an absolute interval upwards."""
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [109.9, 110.1] # Crosses the boundary at 110.0
    })
    alerter = PriceMovementAlerter("TEST_SYMBOL", set())
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 2 # Will trigger fixed level 110.0 and interval
    assert any("fixed price level of 110.00" in msg for msg in alerts)
    assert any("interval price level" in msg for msg in alerts)
    assert any("New level boundary: 110.00" in msg for msg in alerts)

def test_no_repeat_alerts(mock_settings):
    """Test that an alert for a level is not repeated by default."""
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [104.9, 105.1]
    })
    
    # The level 105.0 has already been triggered
    triggered_today = {105.0}
    alerter = PriceMovementAlerter("TEST_SYMBOL", triggered_today)
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 0

def test_allow_repeat_alerts(mock_settings):
    """Test that alerts are repeated if the setting is enabled."""
    # Mock the setting to allow repeats
    mock_settings.return_value.ALLOW_REPEATED_LEVEL_ALERTS = True
    
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [104.9, 105.1]
    })
    
    triggered_today = {105.0} # Pretend it was already triggered
    alerter = PriceMovementAlerter("TEST_SYMBOL", triggered_today)
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 1 # Should still trigger because repeats are allowed
    assert "'TEST_SYMBOL' crossed above fixed price level of 105.00" in alerts[0]

    # Reset mock setting for other tests
    mock_settings.return_value.ALLOW_REPEATED_LEVEL_ALERTS = False

def test_empty_or_missing_config(mock_settings):
    """Test that no errors occur for a symbol with no config."""
    master_df = pd.DataFrame({
        'time': pd.to_datetime(['2025-10-12 10:00:00', '2025-10-12 10:01:00']),
        'close': [104.9, 105.1]
    })
    
    # Use a symbol that is not in the mock config
    alerter = PriceMovementAlerter("UNCONFIGURED_SYMBOL", set())
    alerts = alerter.execute(master_df)
    
    assert len(alerts) == 0
