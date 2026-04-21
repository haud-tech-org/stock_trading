"""
Configuration model - Centralized executor-approach configuration.

Represents complete configuration for a symbol-approach combination.
This is a core domain model used across the entire system.
"""

from dataclasses import dataclass
from typing import Dict, Any

from .trading_hours import TradingHoursConfig


@dataclass(frozen=True)
class ApproachSymbolConfiguration:
    """
    Immutable, complete configuration for a symbol-approach combination.
    
    This object encapsulates ALL settings needed to run an executor for a given
    symbol and approach, including technical parameters, data provider, trading
    hours, and notification settings. It eliminates the need to assemble
    configurations from multiple scattered files.
    
    Key Features:
        - Immutable: Cannot be modified after creation
        - Symbol-aware: Different symbols can have different thresholds
        - Complete: Contains everything needed to run an executor
        - Type-safe: All properties have type hints
        - Self-documenting: Clear property names
    
    Attributes:
        symbol: Trading symbol (e.g., "BTC/USDT:USDT")
        approach: Trading approach name (e.g., "REVERSAL_ANCHOR_SIGNAL_CANDLE")
        resolution: Candle resolution in minutes (e.g., 1, 5, 15, 60)
        approach_config: Symbol-specific approach parameters (thresholds, windows)
        trading_hours: Complete trading hours definition
        trading_hours_name: Reference name to trading hours definition
        display_name: Human-readable name (e.g., "Bitcoin")
        enabled: Whether this configuration is active
        validation_config: Validation settings (period, thresholds)
        notification_config: Notification settings (channels, delays)
    
    Usage:
        config = ConfigurationOrchestrator.get(
            provider="BINANCE",
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
        
        # Access configuration properties
        resolution = config.get_resolution()           # 15
        thresholds = config.get_approach_config()      # {...}
        trading_hours = config.get_trading_hours()     # TradingHoursConfig
    """
    
    # --- Identification ---
    symbol: str
    approach: str
    
    # --- Core Configuration ---
    resolution: int
    approach_config: Dict[str, Any]
    
    # --- Trading Context ---
    trading_hours: TradingHoursConfig
    trading_hours_name: str
    
    # --- Metadata ---
    display_name: str
    enabled: bool
    
    # --- Validation & Notification ---
    validation_config: Dict[str, Any]
    notification_config: Dict[str, Any]
    
    def __post_init__(self):
        """Validate configuration structure"""
        errors = []
        
        if not self.symbol:
            errors.append("Symbol is required")
        
        if not self.approach:
            errors.append("Approach is required")
        
        if self.resolution <= 0:
            errors.append("Resolution must be positive")
        
        if not self.trading_hours:
            errors.append("Trading hours are required")
        
        if errors:
            raise ValueError(f"Configuration validation errors: {'; '.join(errors)}")
    
    # --- Identification Methods ---
    
    def get_symbol(self) -> str:
        """Get the trading symbol"""
        return self.symbol
    
    def get_approach(self) -> str:
        """Get the approach name"""
        return self.approach
    
    def get_display_name(self) -> str:
        """Get human-readable name for this symbol"""
        return self.display_name
    
    # --- Resolution Methods ---
    
    def get_resolution(self) -> int:
        """Get candle resolution in minutes"""
        return self.resolution
    
    # --- Configuration Methods ---
    
    def get_approach_config(self) -> Dict[str, Any]:
        """
        Get approach-specific configuration parameters.
        
        Returns:
            Dictionary containing approach thresholds, windows, and parameters.
            Examples: REVERSAL_STRENGTH_PERCENTAGE, MIN_CANDLES_FOR_REVERSAL, etc.
        """
        return self.approach_config
    
    def get_approach_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific value from approach configuration.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
        
        Returns:
            Configuration value or default if not found
        """
        return self.approach_config.get(key, default)
    
    
    # --- Trading Context Methods ---
    
    def get_trading_hours(self) -> TradingHoursConfig:
        """
        Get complete trading hours definition.
        
        Returns:
            TradingHoursConfig with timezone and sessions
        """
        return self.trading_hours
    
    def get_trading_hours_name(self) -> str:
        """Get reference name to trading hours definition"""
        return self.trading_hours_name
    
    # --- Status Methods ---
    
    def is_enabled(self) -> bool:
        """Check if this configuration is active"""
        return self.enabled
    
    # --- Settings Methods ---
    
    def get_validation_config(self) -> Dict[str, Any]:
        """
        Get validation settings.
        
        Returns:
            Dictionary containing validation_period_minutes, min_profit_threshold, etc.
        """
        return self.validation_config
    
    def get_notification_config(self) -> Dict[str, Any]:
        """
        Get notification settings.
        
        Returns:
            Dictionary containing channels, reminder_delays, etc.
        """
        return self.notification_config
    
    # --- Utility Methods ---
    
    @property
    def cache_key(self) -> str:
        """
        Generate unique cache key for this configuration.
        
        Format: "{symbol}:{approach}"
        
        Returns:
            Unique key suitable for use as dictionary key
        """
        return f"{self.symbol}:{self.approach}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary representation.
        
        Returns:
            Dictionary with all configuration data
        """
        return {
            "symbol": self.symbol,
            "approach": self.approach,
            "resolution": self.resolution,
            "approach_config": self.approach_config,
            "trading_hours_name": self.trading_hours_name,
            "display_name": self.display_name,
            "enabled": self.enabled,
            "validation_config": self.validation_config,
            "notification_config": self.notification_config
        }
    
    def __repr__(self) -> str:
        """Get string representation"""
        return (
            f"ApproachSymbolConfiguration("
            f"symbol={self.symbol}, "
            f"approach={self.approach}, "
            f"resolution={self.resolution}min, "
            f"enabled={self.enabled})"
        )
