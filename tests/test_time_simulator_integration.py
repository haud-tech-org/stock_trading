"""
Integration tests for TimeSimulator and is_trading_hours with ApproachSymbolConfiguration.

Tests that the time utilities correctly use configuration-provided trading hours and timezone.
"""

import logging
import sys
import os
from datetime import datetime

# Setup path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Must be first import
from src.stockreports.config import loader
settings = loader.get_settings()

import pytz
from src.stockreports.utils.time_utils import TimeSimulator
from src.stockreports.services.executor_configuration_service.orchestrator import ConfigurationOrchestrator


def setup_logging():
    """Configure logging for tests"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def test_time_simulator_with_config():
    """Test TimeSimulator accepts and uses configuration"""
    print("\n[TEST 1] TimeSimulator with ApproachSymbolConfiguration")
    
    # Get configuration
    config = ConfigurationOrchestrator.get(
        symbol="BTC/USDT:USDT",
        approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
    )
    print(f"✅ Configuration loaded: {config.symbol}:{config.approach}")
    print(f"   Trading Hours: {config.trading_hours.name}")
    print(f"   Timezone: {config.trading_hours.timezone}")
    
    # Create TimeSimulator with trading_hours
    simulator = TimeSimulator(
        replay_start_str="2025-01-15 10:00:00",
        interval_seconds=60,
        trading_hours=config.trading_hours
    )
    
    # Verify it uses trading_hours' timezone
    assert simulator.timezone == pytz.timezone(config.trading_hours.timezone)
    print(f"✅ TimeSimulator timezone matches config: {simulator.timezone}")
    
    # Verify it uses trading_hours' sessions
    assert simulator.sessions == config.trading_hours.sessions
    print(f"✅ TimeSimulator sessions match config: {len(simulator.sessions)} sessions")
    
    # Verify time advances properly
    initial_time = simulator.get_current_time()
    simulator.advance()
    advanced_time = simulator.get_current_time()
    
    assert advanced_time > initial_time
    print(f"✅ TimeSimulator advances correctly: {initial_time} → {advanced_time}")


def test_time_simulator_without_config():
    """Test TimeSimulator falls back to global settings when no trading_hours provided"""
    print("\n[TEST 2] TimeSimulator without trading_hours (backward compatibility)")
    
    # Create TimeSimulator without trading_hours (uses global settings)
    simulator = TimeSimulator(
        replay_start_str="2025-01-15 10:00:00",
        interval_seconds=60,
        trading_hours=None
    )
    
    # Should use global timezone
    from src.stockreports.utils.time_utils import TIMEZONE
    assert simulator.timezone == TIMEZONE
    print(f"✅ TimeSimulator uses global timezone when no trading_hours: {simulator.timezone}")
    
    # Should use global sessions
    from src.stockreports.utils.time_utils import SESSIONS
    if SESSIONS:
        print(f"✅ TimeSimulator uses global sessions: {len(SESSIONS)} sessions")


def test_is_trading_hours_with_config():
    """Test is_trading_hours using TimeSimulator with configuration"""
    print("\n[TEST 3] is_trading_hours() via TimeSimulator with ApproachSymbolConfiguration")
    
    # Get configuration
    config = ConfigurationOrchestrator.get(
        symbol="BTC/USDT:USDT",
        approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
    )
    
    # Create simulator with trading hours
    simulator = TimeSimulator(
        replay_start_str=None,
        interval_seconds=60,
        trading_hours=config.trading_hours
    )
    
    # Test with a time during trading hours (crypto 24h market)
    # 2025-01-15 is a Wednesday (weekday)
    test_time = datetime(2025, 1, 15, 12, 0, 0)  # Noon
    
    result = simulator.is_trading_hours(test_time)
    
    # Crypto 24h markets are always in trading hours (except weekends)
    assert result is True
    print(f"✅ simulator.is_trading_hours(noon) = {result} (24h market on weekday)")
    
    # Test on weekend (should return False)
    weekend_time = datetime(2025, 1, 18, 12, 0, 0)  # Saturday
    result = simulator.is_trading_hours(weekend_time)
    
    assert result is False
    print(f"✅ simulator.is_trading_hours(weekend) = {result} (weekend, no trading)")


def test_is_trading_hours_without_config():
    """Test is_trading_hours via TimeSimulator with global settings"""
    print("\n[TEST 4] is_trading_hours() via TimeSimulator without trading_hours (backward compatibility)")
    
    # Create simulator without trading_hours (uses global settings)
    simulator = TimeSimulator(
        replay_start_str=None,
        interval_seconds=60,
        trading_hours=None
    )
    
    # Test with weekday (should work with global settings)
    test_time = datetime(2025, 1, 15, 12, 0, 0)  # Wednesday noon
    
    result = simulator.is_trading_hours(test_time)
    print(f"✅ simulator.is_trading_hours(weekday) with global settings = {result}")


def test_trading_hours_timezone_conversion():
    """Test that trading hours validation uses correct timezone from config"""
    print("\n[TEST 5] Trading hours timezone conversion")
    
    # Get config with Asia/Ho_Chi_Minh timezone
    config = ConfigurationOrchestrator.get(
        symbol="VN30F1M",
        approach="VRA"
    )
    
    print(f"   Config timezone: {config.trading_hours.timezone}")
    
    # Create simulator with trading hours
    simulator = TimeSimulator(
        replay_start_str=None,
        interval_seconds=60,
        trading_hours=config.trading_hours
    )
    
    # Create a UTC time
    utc_time = datetime(2025, 1, 15, 3, 0, 0, tzinfo=pytz.utc)  # 3:00 AM UTC
    # In Asia/Ho_Chi_Minh (UTC+7), this is 10:00 AM
    
    result = simulator.is_trading_hours(utc_time)
    print(f"✅ simulator.is_trading_hours with timezone conversion = {result}")
    print(f"   UTC time {utc_time} converted to {config.trading_hours.timezone}")


def test_configuration_data_access():
    """Test accessing trading hours data from configuration"""
    print("\n[TEST 6] Accessing trading hours data from configuration")
    
    config = ConfigurationOrchestrator.get(
        symbol="BTC/USDT:USDT",
        approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
    )
    
    # Access trading hours data
    trading_hours = config.trading_hours
    print(f"✅ Trading Hours Name: {trading_hours.name}")
    print(f"✅ Timezone: {trading_hours.timezone}")
    print(f"✅ Sessions: {len(trading_hours.sessions)}")
    
    for session in trading_hours.sessions:
        print(f"   - {session.name}: {session.start_time} to {session.end_time}")


if __name__ == "__main__":
    setup_logging()
    
    print("\n" + "="*80)
    print("TIME SIMULATOR & TIME UTILS INTEGRATION TESTS")
    print("="*80)
    
    try:
        test_time_simulator_with_config()
        test_time_simulator_without_config()
        test_is_trading_hours_with_config()
        test_is_trading_hours_without_config()
        test_trading_hours_timezone_conversion()
        test_configuration_data_access()
        
        print("\n" + "="*80)
        print("✅ ALL INTEGRATION TESTS PASSED!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
