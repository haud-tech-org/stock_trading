"""
Phase 1 Integration Tests - Multi-Provider Data Retrieval System

Tests the complete Phase 1 implementation:
- Provider framework (base, factory, registry)
- Vietstock provider integration
- Data normalization
- Central coordinator
- Backward compatibility wrapper
- Configuration management

These tests ensure all components work together correctly.
"""

import sys
import pytest
import pandas as pd
from datetime import datetime, timedelta
import pytz
from typing import Dict, Any

from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider
from src.stockreports.data_services._internal.providing._provider_factory import ProviderFactory
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing._registry import register_all_providers, get_provider, list_providers
from src.stockreports.data_services._internal.providing._coordinator import DataProviderCoordinator
from src.stockreports.data_services._internal.providing.vietstock.provider import VietstockProvider
from src.stockreports.data_services._internal.providing.vietstock.normalizer import VietstockNormalizer
from src.stockreports.config import settings


class TestPhase1Integration:
    """Phase 1 integration test suite."""
    
    @classmethod
    def setup_class(cls):
        """Setup for all tests - register providers."""
        ProviderFactory._providers.clear()
        ProviderFactory._instances.clear()
        register_all_providers()
    
    def test_provider_framework_base_class(self):
        """Test BaseDataProvider abstract class."""
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseDataProvider("test")
        
        # Should be able to subclass
        class TestProvider(BaseDataProvider):
            def fetch_ohlcv(self, symbol, from_ts, to_ts, timeframe="1m"):
                return pd.DataFrame()
            def validate_symbol(self, symbol):
                return True
            def get_supported_timeframes(self):
                return ["1m"]
            def normalize_response(self, raw_data):
                return pd.DataFrame()
        
        provider = TestProvider("test")
        assert provider.provider_name == "test"
        assert provider.validate_symbol("TEST")
        assert provider.get_supported_timeframes() == ["1m"]
    
    def test_provider_factory_registration(self):
        """Test ProviderFactory registration mechanism."""
        # Should have Vietstock registered
        providers = list_providers()
        assert "vietstock" in providers, f"Vietstock not in {providers}"
        
        # Should be able to get provider
        provider = get_provider("vietstock")
        assert isinstance(provider, VietstockProvider)
        
        # Should raise error for unknown provider
        with pytest.raises(ValueError):
            get_provider("unknown_provider")
    
    def test_vietstock_provider_interface(self):
        """Test VietstockProvider implements interface correctly."""
        provider = get_provider("vietstock")
        
        # Check all required methods exist and are callable
        assert callable(provider.fetch_ohlcv)
        assert callable(provider.validate_symbol)
        assert callable(provider.get_supported_timeframes)
        assert callable(provider.normalize_response)
        assert callable(provider.validate_configuration)
        
        # Check properties
        assert provider.provider_name == "vietstock"
        assert provider.validate_configuration() == True
        
        # Check timeframes (VietStock returns numeric resolutions in minutes)
        timeframes = provider.get_supported_timeframes()
        assert len(timeframes) > 0
        assert 1 in timeframes  # 1 minute
        assert 1440 in timeframes  # 1440 minutes = 1 day
        assert all(isinstance(tf, int) for tf in timeframes)
    
    def test_vietstock_symbol_validation(self):
        """Test symbol validation for Vietstock."""
        provider = get_provider("vietstock")
        
        # Valid symbols should pass
        assert provider.validate_symbol("VN30") == True
        assert provider.validate_symbol("VNM") == True
        assert provider.validate_symbol("TPB") == True
        
        # Invalid symbols should raise
        with pytest.raises(ValueError):
            provider.validate_symbol("")
        
        with pytest.raises(ValueError):
            provider.validate_symbol("123456")  # Too long
        
        with pytest.raises(ValueError):
            provider.validate_symbol("VN@30")  # Invalid chars
    
    def test_vietstock_normalizer(self):
        """Test VietstockNormalizer converts data correctly."""
        normalizer = VietstockNormalizer()
        
        now_ts = int(datetime.now().timestamp())
        raw_data = {
            's': 'VN30',
            't': [now_ts - 300, now_ts - 240, now_ts - 180],
            'o': [1000.0, 1001.0, 1002.0],
            'h': [1001.0, 1002.0, 1003.0],
            'l': [999.0, 1000.0, 1001.0],
            'c': [1000.5, 1001.5, 1002.5],
            'v': [100, 200, 300]
        }
        
        df = normalizer.normalize(raw_data, 'VN30')
        
        # Check shape
        assert len(df) == 3
        assert len(df.columns) == 5
        
        # Check columns
        expected_cols = ['open', 'high', 'low', 'close', 'volume']
        assert list(df.columns) == expected_cols
        
        # Check index
        assert isinstance(df.index, pd.DatetimeIndex)
        assert df.index.tz is not None
        assert str(df.index.tz) == 'Asia/Ho_Chi_Minh'
        
        # Check data types
        assert df['volume'].dtype in ['int64', 'float64']
        assert df['open'].dtype == 'float64'
        
        # Check OHLCV validation
        assert normalizer.validate_ohlcv(df) == True
    
    def test_normalizer_error_handling(self):
        """Test normalizer error handling."""
        normalizer = VietstockNormalizer()
        
        # Missing fields
        with pytest.raises(ValueError):
            normalizer.normalize({'s': 'VN30', 't': [1]}, 'VN30')
        
        # Array length mismatch
        with pytest.raises(ValueError):
            normalizer.normalize({
                's': 'VN30',
                't': [1, 2],
                'o': [1],  # Wrong length
                'h': [1, 2],
                'l': [1, 2],
                'c': [1, 2],
                'v': [1, 2]
            }, 'VN30')
        
        # Empty data
        with pytest.raises(ValueError):
            normalizer.normalize({
                's': 'VN30',
                't': [],
                'o': [],
                'h': [],
                'l': [],
                'c': [],
                'v': []
            }, 'VN30')
    
    def test_data_provider_coordinator(self):
        """Test DataProviderCoordinator stateless operation."""
        coordinator = DataProviderCoordinator()
        
        # Check available providers
        providers = coordinator.list_available_providers()
        assert "vietstock" in providers
        
        # Get provider instance
        instance = coordinator.get_provider_instance(Provider.VIETSTOCK)
        assert isinstance(instance, VietstockProvider)
        
        # Check supported timeframes
        timeframes = coordinator.get_supported_timeframes(Provider.VIETSTOCK)
        assert len(timeframes) > 0
    
    def test_coordinator_explicit_provider_passing(self):
        """Test that coordinator requires explicit provider specification."""
        coordinator = DataProviderCoordinator()
        
        # Symbol validation requires explicit provider
        assert coordinator.validate_symbol("VN30", Provider.VIETSTOCK) == True
        
        # Timeframe checking requires explicit provider
        timeframes = coordinator.get_supported_timeframes(Provider.VIETSTOCK)
        assert len(timeframes) > 0
        
        # Configuration validation requires explicit provider
        assert coordinator.validate_configuration(Provider.VIETSTOCK) == True
    
    def test_coordinator_validation(self):
        """Test validation methods in coordinator."""
        coordinator = DataProviderCoordinator()
        
        # Symbol validation with explicit provider
        assert coordinator.validate_symbol("VN30", Provider.VIETSTOCK) == True
        
        with pytest.raises(ValueError):
            coordinator.validate_symbol("", Provider.VIETSTOCK)
        
        # Configuration validation with explicit provider
        assert coordinator.validate_configuration(Provider.VIETSTOCK) == True
        
        # Timeframe support with explicit provider (VietStock returns numeric resolutions in minutes)
        timeframes = coordinator.get_supported_timeframes(Provider.VIETSTOCK)
        assert 1 in timeframes  # 1 minute resolution
        assert 1440 in timeframes  # 1 day = 1440 minutes
    
    def test_coordinator_health_check(self):
        """Test coordinator health check."""
        coordinator = DataProviderCoordinator()
        
        health = coordinator.health_check()
        
        # Check structure
        assert 'available_providers' in health
        assert 'enabled_providers' in health
        assert 'provider_status' in health
        
        # Check values
        assert 'vietstock' in health['available_providers']
        
        # Check provider status
        vietstock_status = health['provider_status']['vietstock']
        assert vietstock_status['available'] == True
        assert vietstock_status['configured'] == True
    
    def test_backward_compatibility_wrapper(self):
        """Test coordinator wrapper functions directly."""
        # Ensure all providers are registered
        try:
            register_all_providers()
        except ValueError:
            pass
        
        # Should be able to get available providers
        providers = list_providers()
        assert "vietstock" in providers
        
        # Should be able to validate symbols via coordinator
        coordinator = DataProviderCoordinator()
        assert coordinator.validate_symbol("VN30", Provider.VIETSTOCK) == True
        
        with pytest.raises(ValueError):
            coordinator.validate_symbol("", Provider.VIETSTOCK)
    
    def test_configuration_settings(self):
        """Test that provider configuration is in settings."""
        # Import data provider settings from the loader
        from src.stockreports.config.loader import get_data_provider_settings
        data_provider_settings = get_data_provider_settings()
        
        # Check required settings exist
        assert hasattr(data_provider_settings, 'ENABLED_DATA_PROVIDERS')
        assert hasattr(data_provider_settings, 'DATA_PROVIDER_CONFIG')
        assert hasattr(data_provider_settings, 'PROVIDER_SYMBOLS_CONFIG')
        
        # Check values
        assert "vietstock" in data_provider_settings.ENABLED_DATA_PROVIDERS
        assert "vietstock" in data_provider_settings.DATA_PROVIDER_CONFIG
        assert data_provider_settings.DATA_PROVIDER_CONFIG["vietstock"]["enabled"] == True
        assert "vietstock" in data_provider_settings.PROVIDER_SYMBOLS_CONFIG
    
    def test_end_to_end_workflow(self):
        """Test complete end-to-end workflow with explicit providers."""
        # Step 1: Get coordinator
        coordinator = DataProviderCoordinator()
        assert coordinator is not None
        
        # Step 2: Validate symbol with explicit provider
        assert coordinator.validate_symbol("VN30", Provider.VIETSTOCK) == True
        
        # Step 3: Check timeframes for specific provider
        timeframes = coordinator.get_supported_timeframes(Provider.VIETSTOCK)
        assert len(timeframes) > 0
        
        # Step 4: Get provider info
        info = coordinator.get_provider_info(Provider.VIETSTOCK)
        assert info['name'] == 'vietstock'
        assert info['enabled'] == True
        
        # Step 5: Health check
        health = coordinator.health_check()
        assert health['provider_status']['vietstock']['available'] == True
        
        # Step 6: Verify available providers
        providers = list_providers()
        assert "vietstock" in providers


def run_integration_tests():
    """Run all integration tests."""
    print("=" * 70)
    print("Phase 1 Integration Tests")
    print("=" * 70)
    
    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-ra"
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_integration_tests()
    sys.exit(exit_code)
