# src/stockreports/config/loader.py
import importlib
from . import settings as settings_module
from . import signal_settings as signal_settings_module
from . import notification_settings as notification_settings_module
from . import validation_settings as validation_settings_module

def load_config():
    """
    Dynamically reloads all settings modules. This should be called once
    at the start of the application or process.
    """
    importlib.reload(settings_module)
    importlib.reload(signal_settings_module)
    importlib.reload(notification_settings_module)
    importlib.reload(validation_settings_module)
    
    # The return is kept for the main script's initial load, but getters are preferred elsewhere.
    return settings_module, signal_settings_module, notification_settings_module, validation_settings_module

def get_settings():
    """Returns the currently loaded main settings module."""
    return settings_module

def get_signal_settings():
    """Returns the currently loaded signal settings module."""
    return signal_settings_module

def get_notification_settings():
    """Returns the currently loaded notification settings module."""
    return notification_settings_module

def get_validation_settings():
    """Returns the currently loaded validation settings module."""
    return validation_settings_module
