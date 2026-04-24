import pytest
from src.stockreports.services.external.notification_services._internal.channels.ntfy_channel import NtfyNotificationChannel
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.services.external.notification_services._internal.channel_type import ChannelType

class DummyConfig:
    def __init__(self, topics=None):
        self.NTFY_ENABLED = True
        self.NTFY_TOPICS = topics or ["testtopic"]

def test_ntfy_send(monkeypatch):
    sent = []
    def mock_post(url, data, headers):
        sent.append((url, data, headers))
        class Resp: pass
        return Resp()
    monkeypatch.setattr("requests.post", mock_post)
    config = DummyConfig(["testtopic"])
    channel = NtfyNotificationChannel(config)
    notification = AlertNotification(
        symbol="BTC/USDT:USDT",
        approach="REVERSAL_ANCHOR_SIGNAL_CANDLE",
        signal="BUY",
        alert_price=100.0,
        alert_time=1,
        details=None,
        suggested_price=None,
        suggested_profit_threshold=None
    )
    channel.send(notification)
    assert sent
    assert sent[0][0] == "https://ntfy.sh/testtopic"
    assert b"Time:" in sent[0][1]
    assert "Title" in sent[0][2]

def test_ntfy_validate_config():
    config = DummyConfig(["topic1"])
    NtfyNotificationChannel(config)  # Should not raise
    config = DummyConfig([])
    config.NTFY_ENABLED = True
    config.NTFY_TOPICS = []
    with pytest.raises(ValueError):
        NtfyNotificationChannel(config).validate_config()
