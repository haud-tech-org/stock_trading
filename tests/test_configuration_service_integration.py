"""
Integration test for the Executor Configuration Service.

Tests core functionality:
1. Singleton pattern
2. Configuration loading
3. Configuration caching
4. Backward compatibility adapters
"""

import sys
import logging
from pathlib import Path
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_configuration_service():
    """Test the executor configuration service end-to-end"""
    
    logger.info("=" * 70)
    logger.info("EXECUTOR CONFIGURATION SERVICE INTEGRATION TEST")
    logger.info("=" * 70)
    
    # Test 1: Import Configuration Service
    logger.info("\n[TEST 1] Importing Executor Configuration Service...")
    try:
        from src.stockreports.services.executor_configuration_service import (
            ExecutorConfigurationOrchestrator,
            ApproachSymbolConfiguration,
            ExecutorConfigurationError
        )
        logger.info("✅ Executor configuration service imported successfully")
    except ImportError as e:
        logger.error(f"❌ Failed to import executor configuration service: {e}")
        return False
    
    # Test 2: Get configuration
    logger.info("\n[TEST 2] Getting configuration for BTC/USDT:USDT...")
    try:
        config = ExecutorConfigurationOrchestrator.get(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
        logger.info(f"✅ Configuration loaded: {config}")
        logger.info(f"   - Symbol: {config.get_symbol()}")
        logger.info(f"   - Approach: {config.get_approach()}")
        logger.info(f"   - Resolution: {config.get_resolution()} minutes")
        logger.info(f"   - Display Name: {config.get_display_name()}")
        logger.info(f"   - Enabled: {config.is_enabled()}")
    except Exception as e:
        logger.error(f"❌ Failed to get configuration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Access configuration properties
    logger.info("\n[TEST 3] Accessing configuration properties...")
    try:
        approach_config = config.get_approach_config()
        trading_hours = config.get_trading_hours()
        
        logger.info(f"✅ Approach Config Keys: {list(approach_config.keys())}")
        logger.info(f"✅ Trading Hours: {trading_hours.get_sessions_summary()}")
    except Exception as e:
        logger.error(f"❌ Failed to access properties: {e}")
        return False
    
    # Test 4: Cache effectiveness
    logger.info("\n[TEST 4] Testing cache effectiveness...")
    try:
        import time
        
        # First call (cache miss)
        start = time.time()
        config1 = ExecutorConfigurationOrchestrator.get(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
        first_time = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        config2 = ExecutorConfigurationOrchestrator.get(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
        second_time = time.time() - start
        
        logger.info(f"✅ First call (cache miss): {first_time*1000:.2f}ms")
        logger.info(f"✅ Second call (cache hit): {second_time*1000:.2f}ms")
        logger.info(f"✅ Cache speedup: {first_time/second_time:.1f}x faster")
        
        # Verify same instance
        if config1.cache_key == config2.cache_key:
            logger.info("✅ Same configuration retrieved from cache")
        else:
            logger.error("❌ Different configurations retrieved")
            return False
    except Exception as e:
        logger.error(f"❌ Cache test failed: {e}")
        return False
    
    # Test 5: Singleton pattern
    logger.info("\n[TEST 5] Testing singleton pattern...")
    try:
        orchestrator1 = ExecutorConfigurationOrchestrator()
        orchestrator2 = ExecutorConfigurationOrchestrator()
        
        if orchestrator1 is orchestrator2:
            logger.info("✅ Singleton pattern verified (same instance)")
        else:
            logger.error("❌ Singleton pattern failed (different instances)")
            return False
    except Exception as e:
        logger.error(f"❌ Singleton test failed: {e}")
        return False
    
    # Test 6: Get supported symbols
    logger.info("\n[TEST 6] Getting supported symbols and approaches...")
    try:
        symbols = ExecutorConfigurationOrchestrator.get_supported_symbols()
        logger.info(f"✅ All symbols: {symbols}")
        
        approaches = ExecutorConfigurationOrchestrator.get_supported_approaches(
            "BTC/USDT:USDT"
        )
        logger.info(f"✅ BTC/USDT:USDT approaches: {approaches}")
    except Exception as e:
        logger.error(f"❌ Failed to get supported symbols/approaches: {e}")
        return False
    
    # Test 7: Adapter layer
    logger.info("\n[TEST 7] Testing adapter layer...")
    try:
        from src.stockreports.services.executor_configuration_service.adapters import (
            get_adapter,
            get_configuration_v2
        )
        
        # Test adapter
        adapter = get_adapter()
        config = adapter.get_approach_config(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
        logger.info(f"✅ Adapter retrieved configuration: {config.get_symbol()}")
    except Exception as e:
        logger.error(f"❌ Adapter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 8: Cache statistics
    logger.info("\n[TEST 8] Cache statistics...")
    try:
        stats = ExecutorConfigurationOrchestrator.get_cache_stats()
        logger.info(f"✅ Cache size: {stats['cache_size']}")
        logger.info(f"✅ Cached keys: {stats['cached_keys']}")
    except Exception as e:
        logger.error(f"❌ Cache stats failed: {e}")
        return False
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ ALL TESTS PASSED!")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = test_configuration_service()
    sys.exit(0 if success else 1)
