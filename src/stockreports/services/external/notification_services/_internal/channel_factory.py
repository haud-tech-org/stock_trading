"""
ChannelFactory - Creates and manages notification channel instances.
"""

# --- Python Standard Library ---
from typing import Dict, Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from .channels.email_channel import EmailNotificationChannel
from .channels.sms_channel import SMSNotificationChannel
from .channels.ntfy_channel import NtfyNotificationChannel
from .channels.slack_channel import SlackNotificationChannel
from .channel_type import ChannelType
from .channels.base_channel import BaseNotificationChannel


class ChannelFactory:
    _instance = None

    def __new__(cls, config: object):
        if cls._instance is None:
            cls._instance = super(ChannelFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: object) -> None:
        if getattr(self, '_initialized', False):
            return
        self.config = config
        self._instances: Dict[str, object] = {}
        self._initialized = True

    def get_channel(self, channel_name: str | ChannelType) -> Optional[BaseNotificationChannel]:
        # Accept both enum and string for backward compatibility
        if isinstance(channel_name, ChannelType):
            key = channel_name.value
        else:
            key = str(channel_name).upper()
        if key not in self._instances:
            if key == ChannelType.EMAIL.value:
                self._instances[key] = EmailNotificationChannel(self.config)
            elif key == ChannelType.SMS.value:
                self._instances[key] = SMSNotificationChannel(self.config)
            elif key == ChannelType.NTFY.value:
                self._instances[key] = NtfyNotificationChannel(self.config)
            elif key == ChannelType.SLACK.value:
                self._instances[key] = SlackNotificationChannel(self.config)
            else:
                return None
        return self._instances[key]
