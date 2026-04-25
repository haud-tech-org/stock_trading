import pytest
import pandas as pd
from src.stockreports.alert.announce.approach.LARGE_CANDLE.alerter import LargeCandleAlerter
from src.stockreports.alert.common.constants import CandleColumn

class DummyLogger:
    def info(self, msg):
        pass

def test_large_candle_alerter_triggers_alert(monkeypatch):
    # Setup
    data = [
        {
            CandleColumn.OPEN: 700,
            CandleColumn.CLOSE: 1100,
            CandleColumn.HIGH: 1200,
            CandleColumn.LOW: 600,
        },
    ]
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(["2024-04-25 10:00:00"])
    monkeypatch.setattr(
        "src.stockreports.alert.alerter.Alerter.get_approach_config",
        lambda symbol, approach: {"BODY_THRESHOLD": 500}
    )
    alerter = LargeCandleAlerter(symbol="BTCUSDT")
    monkeypatch.setattr("src.stockreports.alert.announce.approach.LARGE_CANDLE.alerter.logger", DummyLogger())
    # Act
    result = alerter.run(df)
    # Assert
    assert result.confirmed_alerts, "Should trigger alert for large candle"
    alert = result.confirmed_alerts[0]
    assert alert.magnitude == 600
    assert alert.signal in ("PRICE_UP", "PRICE_DOWN")

def test_large_candle_alerter_no_alert(monkeypatch):
    data = [
        {
            CandleColumn.OPEN: 1020,
            CandleColumn.CLOSE: 1030,
            CandleColumn.HIGH: 1050,
            CandleColumn.LOW: 1000,
        },
    ]
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(["2024-04-25 10:05:00"])
    monkeypatch.setattr(
        "src.stockreports.alert.alerter.Alerter.get_approach_config",
        lambda symbol, approach: {"BODY_THRESHOLD": 100}
    )
    alerter = LargeCandleAlerter(symbol="BTCUSDT")
    result = alerter.run(df)
    assert not result.confirmed_alerts, "Should not trigger alert if range below threshold"
