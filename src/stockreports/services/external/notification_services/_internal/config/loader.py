"""
NotificationConfigLoader - Loads and validates hierarchical notification config.
"""


# --- Python Standard Library ---
import json
import os
from typing import Any, Dict, Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.model.signal_type import SignalType
from src.stockreports.utils.file_utils import get_project_root

class NotificationConfigLoader:
    @staticmethod
    def load(config_path: Optional[str] = None) -> 'NotificationConfig':
        import logging
        logger = logging.getLogger(__name__)
        config_data = None
        # Default path: src/stockreports/config/notification_service_config.json
        if config_path is None:
            project_root = get_project_root()
            config_path = os.path.join(project_root, "src", "stockreports", "config", "notification_service_config.json")
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load notification config from {config_path}: {e}")
        else:
            logger.error(f"Notification config file not found or path not provided: {config_path}. No config loaded.")
        if config_data is None:
            logger.error("Notification config is missing or could not be loaded. Functionality may be impaired.")
        return NotificationConfig(config_data or {})


class NotificationConfig:
    def __init__(self, config_data: Dict[str, Any]):
        self.data = config_data

    def is_signal_enabled(self, symbol: str, approach: str, signal: SignalType | str) -> bool:
        # Accept both enum and string signals
        if hasattr(signal, 'value'):
            sig_key = signal.value
        else:
            sig_key = str(signal).strip().upper().replace(" ", "_")
        try:
            channels = self.data.get("symbols", {}).get(symbol, {}).get("approaches", {}).get(approach, {}).get("channels", {})
            for channel_cfg in channels.values():
                if channel_cfg.get("enabled") and channel_cfg.get("signals", {}).get(sig_key, {}).get("enabled"):
                    return True
            return False
        except Exception:
            return False

    def get_enabled_channels(self, symbol: str, approach: str, signal: SignalType | str) -> list[str]:
        if hasattr(signal, 'value'):
            sig_key = signal.value
        else:
            sig_key = str(signal).strip().upper().replace(" ", "_")
        try:
            channels = self.data.get("symbols", {}).get(symbol, {}).get("approaches", {}).get(approach, {}).get("channels", {})
            return [name for name, cfg in channels.items() if cfg.get("enabled") and cfg.get("signals", {}).get(sig_key, {}).get("enabled")]
        except Exception:
            return []
