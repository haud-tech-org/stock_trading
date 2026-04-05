# src/stockreports/data_processor/settings.py
"""
DataProcessor Configuration Settings
"""

from src.stockreports.config import loader


class DataProcessorSettings:
    """DataProcessor configuration settings."""
    
    def __init__(self):
        """Initialize DataProcessor settings by loading from main config."""
        settings = loader.get_settings()
        
        # Load configuration for which transformations to apply
        self._config = getattr(settings, 'DATA_PROCESSING', {
            'timezone_conversion': True,
            'price_adjustment': True,
        })
        
        # Set private configurations for properties
        self._timezone_conversion = self._config.get('timezone_conversion', True)
        self._price_adjustment = self._config.get('price_adjustment', True)
    
    def get_configuration_status(self) -> dict:
        """
        Get the status of all DataProcessor configuration properties.
        
        Returns:
            dict: Dictionary with configuration status
                {
                    'timezone_conversion': bool,
                    'price_adjustment': bool
                }
        """
        return {
            'timezone_conversion': self.is_enabled_timezone_conversion(),
            'price_adjustment': self.is_enabled_price_adjustment(),
        }
    
    def is_enabled_timezone_conversion(self) -> bool:
        """Check if timezone conversion is enabled."""
        return self._timezone_conversion
    
    def is_enabled_price_adjustment(self) -> bool:
        """Check if price adjustment is enabled."""
        return self._price_adjustment


# Create a singleton instance of DataProcessorSettings
_instance = None


def get_processor_settings() -> DataProcessorSettings:
    """
    Get or create the DataProcessorSettings instance.
    
    Returns:
        DataProcessorSettings instance
    """
    global _instance
    if _instance is None:
        _instance = DataProcessorSettings()
    return _instance


def reload_processor_settings():
    """Reload the DataProcessorSettings instance."""
    global _instance
    _instance = DataProcessorSettings()
    return _instance
