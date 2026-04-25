import pytest


import pandas as pd
import pytest
from unittest.mock import patch
from src.stockreports.alert.announce.approach.LARGE_VOLUME_CANDLE.alerter import LargeVolumeCandleAlerter

@pytest.fixture
def sample_df():
    return pd.DataFrame([
        {"volume": 100},
        {"volume": 250},
    ])



@patch("src.stockreports.alert.alerter.Alerter.get_approach_config", return_value={"MULTIPLIER_VOLUME": 2})
def test_execute_alert(mock_get_config):
    df = pd.DataFrame([
        {"volume": 100},
        {"volume": 250},
    ])
    alerter = LargeVolumeCandleAlerter(symbol="TEST")
    result = alerter.execute(df)
    assert result is not None
    assert result["latest_volume"] == 250
    assert result["nearest_volume"] == 100
    assert result["multiplier"] == 2


@patch("src.stockreports.alert.alerter.Alerter.get_approach_config", return_value={"MULTIPLIER_VOLUME": 2})
def test_execute_no_alert(mock_get_config):
    df = pd.DataFrame([
        {"volume": 100},
        {"volume": 150},
    ])
    alerter = LargeVolumeCandleAlerter(symbol="TEST")
    result = alerter.execute(df)
    assert result is None
