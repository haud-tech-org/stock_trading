# src/stockreports/config/loader.py
import importlib
from . import settings as settings_module
from . import signal_settings as signal_settings_module

def load_config():
    """
    Dynamically reloads the settings modules to ensure the latest
    configuration is always used, bypassing Python's module cache.

    Returns:
        A tuple containing the reloaded (settings, signal_settings) modules.
    """
    importlib.reload(settings_module)
    importlib.reload(signal_settings_module)
    return settings_module, signal_settings_module
