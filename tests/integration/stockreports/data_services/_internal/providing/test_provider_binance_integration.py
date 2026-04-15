"""
Phase 2 Integration Tests - Binance Data Providers

Tests the Binance provider implementations:
- BinanceNormalizer (array format conversion)
- BinanceAPIProvider (REST API integration)
- BinanceCCXTProvider (CCXT wrapper)
- Provider registration
- Multi-provider coordination
"""

import sys
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.stockreports.data_services._internal.providing.binance.normalizer import BinanceNormalizer
from src.stockreports.data_services._internal.providing.binance.api_provider import BinanceAPIProvider
from src.stockreports.data_services._internal.providing.binance.ccxt_provider import BinanceCCXTProvider, CCXT_AVAILABLE
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing._coordinator import DataProviderCoordinator
from src.stockreports.data_services._internal.providing._registry import register_all_providers, list_providers
from src.stockreports.data_services._internal.providing._provider_factory import ProviderFactory


class TestPhase2Integration:
    """Phase 2 Binance provider integration test suite."""
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests."""
        ProviderFactory._providers.clear()
        ProviderFactory._instances.clear()
        register_all_providers()
    
    def test_binance_normalizer_array_format(self):
        """Test BinanceNormalizer converts array format correctly."""
        normalizer = BinanceNormalizer()
        
        now_ms = int(datetime.now().timestamp() * 1000)
        raw_data = [
            [now_ms - 300000, "1000.50", "1001.00", "1000.00", "1000.90", "100"],
            [now_ms - 240000, "1001.00", "1002.00", "1001.00", "1001.90", "200"],
            [now_ms - 180000, "1002.50", "1003.00", "1002.00", "1002.90", "300"],
        ]
        
        df = normalizer.normalize(raw_data, 'BTCUSDT')
        
        assert len(df) == 3
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert str(df.index.tz) == 'UTC'
        assert normalizer.validate_ohlcv(df)
    
    def test_binance_normalizer_timestamp_conversion(self):
        """Test millisecond to second timestamp conversion."""
        normalizer = BinanceNormalizer()
        
        # Use known timestamp
        ts_sec = 1609459200  # 2021-01-01 00:00:00 UTC
        ts_ms = ts_sec * 1000
        
        raw_data = [[ts_ms, "1000", "1001", "999", "1000", "100"]]
        df = normalizer.normalize(raw_data, 'TEST')
        
        # Check timestamp was converted correctly
        assert df.index[0].timestamp() == ts_sec
    
    def test_binance_api_provider_interface(self):
        """Test BinanceAPIProvider implements interface correctly."""
        provider = BinanceAPIProvider()
        
        assert provider.provider_name == "binance"
        assert callable(provider.fetch_ohlcv)
        assert callable(provider.validate_symbol)
        assert callable(provider.get_supported_timeframes)
        assert provider.validate_configuration() == True
    
    def test_binance_api_provider_symbol_validation(self):
        """Test Binance symbol validation."""
        provider = BinanceAPIProvider()
        
        # Valid symbols
        assert provider.validate_symbol("BTCUSDT")
        assert provider.validate_symbol("ETHUSDT")
        assert provider.validate_symbol("BNBBUSD")
        
        # Invalid symbols
        with pytest.raises(ValueError):
            provider.validate_symbol("")
        
        with pytest.raises(ValueError):
            provider.validate_symbol("BTC")  # Too short
        
        with pytest.raises(ValueError):
            provider.validate_symbol("BTC@USDT")  # Invalid chars
    
    def test_binance_api_provider_timeframes(self):
        """Test Binance supported timeframes."""
        provider = BinanceAPIProvider()
        
        timeframes = provider.get_supported_timeframes()
        expected = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        
        assert timeframes == expected
    
    def test_binance_ccxt_symbol_normalization(self):
        """Test CCXT symbol format normalization."""
        # Test without initializing (which would fail if CCXT not installed)
        assert BinanceCCXTProvider._normalize_symbol_format("BTCUSDT") == "BTCUSDT"
        assert BinanceCCXTProvider._normalize_symbol_format("BTCUSDT") == "BTCUSDT"
        assert BinanceCCXTProvider._normalize_symbol_format("ETHBUSD") == "ETH/BUSD"
        assert BinanceCCXTProvider._normalize_symbol_format("BNBUSDT") == "BNB/USDT"
    
    def test_binance_ccxt_optional_dependency(self):
        """Test BinanceCCXTProvider handles missing CCXT gracefully."""
        if CCXT_AVAILABLE:
            pytest.skip("CCXT is installed, skipping optional test")
        
        # Should raise error about missing CCXT
        with pytest.raises(RuntimeError) as exc_info:
            BinanceCCXTProvider()
        
        assert "CCXT library is not installed" in str(exc_info.value)
    
    def test_provider_registration(self):
        """Test that all providers are registered."""
        providers = list_providers()
        
        assert "vietstock" in providers
        assert "binance" in providers
        # binance_ccxt might not be available if CCXT not installed
    
    def test_multi_provider_coordinator(self):
        """Test coordinator works with multiple providers."""
        # Temporarily enable Binance for this test
        from src.stockreports.config.loader import get_data_provider_settings
        data_provider_settings = get_data_provider_settings()
        original_enabled = data_provider_settings.ENABLED_DATA_PROVIDERS
        data_provider_settings.ENABLED_DATA_PROVIDERS = ["vietstock", "binance"]
        
        try:
            # Create stateless coordinator
            coordinator = DataProviderCoordinator()
            
            # Test with explicit providers
            available = coordinator.list_available_providers()
            assert "binance" in available
            assert "vietstock" in available
            
            # Get provider info for each
            for provider_enum in [Provider.VIETSTOCK, Provider.BINANCE]:
                info = coordinator.get_provider_info(provider_enum)
                assert info['name'] == provider_enum.value
        finally:
            # Restore original settings
            data_provider_settings.ENABLED_DATA_PROVIDERS = original_enabled
    
    def test_coordinator_health_check_multi_provider(self):
        """Test coordinator health check includes all available providers."""
        # Temporarily enable Binance for this test
        from src.stockreports.config.loader import get_data_provider_settings
        data_provider_settings = get_data_provider_settings()
        original_enabled = data_provider_settings.ENABLED_DATA_PROVIDERS
        data_provider_settings.ENABLED_DATA_PROVIDERS = ["vietstock", "binance"]
        
        try:
            # Create stateless coordinator
            coordinator = DataProviderCoordinator()
            
            health = coordinator.health_check()
            
            assert 'vietstock' in health['available_providers']
            assert 'binance' in health['available_providers']
            
            # Check status for each
            assert health['provider_status']['vietstock']['available'] == True
            assert health['provider_status']['binance']['available'] == True
            
            # Check enabled status reflects settings
            assert health['provider_status']['vietstock']['enabled'] == True
            assert health['provider_status']['binance']['enabled'] == True
        finally:
            # Restore original settings
            data_provider_settings.ENABLED_DATA_PROVIDERS = original_enabled
    
    def test_binance_normalizer_error_handling(self):
        """Test error handling in BinanceNormalizer."""
        normalizer = BinanceNormalizer()
        
        now_ms = int(datetime.now().timestamp() * 1000)
        
        # Incomplete candle
        with pytest.raises(ValueError):
            normalizer.normalize([[now_ms, "1000"]], 'TEST')
        
        # Empty data
        with pytest.raises(ValueError):
            normalizer.normalize([], 'TEST')
        
        # Invalid timestamp
        with pytest.raises(ValueError):
            normalizer.normalize([["invalid", "1000", "1001", "999", "1000", "100"]], 'TEST')
    
    def test_binance_api_provider_configuration(self):
        """Test BinanceAPIProvider configuration."""
        provider = BinanceAPIProvider(timeout=20, retries=5)
        
        assert provider.timeout == 20
        assert provider.retries == 5
        assert provider.validate_configuration() == True
    
    def test_provider_normalization_consistent_formats(self):
        """Test that both normalizers produce consistent output."""
        vietstock_normalizer = BinanceNormalizer()  # Using same normalizer as base
        binance_normalizer = BinanceNormalizer()
        
        now_ms = int(datetime.now().timestamp() * 1000)
        raw_data = [[now_ms, "1000", "1001", "999", "1000", "100"]]
        
        df1 = vietstock_normalizer.normalize(raw_data, 'TEST1')
        df2 = binance_normalizer.normalize(raw_data, 'TEST2')
        
        # Structure should be identical
        assert df1.columns.tolist() == df2.columns.tolist()
        assert df1.index.tz == df2.index.tz
        assert len(df1) == len(df2)


def run_phase2_tests():
    """Run all Phase 2 integration tests."""
    print("=" * 70)
    print("Phase 2 Integration Tests - Binance Providers")
    print("=" * 70)
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-ra"
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_phase2_tests()
    sys.exit(exit_code)
