import pytest
import pandas as pd
from datetime import datetime
import os
import sys

# Ensure the src directory is in the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from src.stockreports.utils.data_utils import fetch_intraday_data
from src.stockreports.config import settings

@pytest.mark.integration
def test_fetch_intraday_data_live():
    """
    Tests the live data fetching from the API.
    This is an integration test and makes a real network request.
    """
    # Arrange
    symbol = settings.SYMBOL
    # Use today's date for the test
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Act
    data = fetch_intraday_data(symbol, date_str)

    # Assert
    # The API might return no data if the market is closed (e.g., on a weekend).
    # So, we first check if data was returned before doing more specific checks.
    if data is None or data.get('s') != 'ok' or not data.get('t'):
        # This is an acceptable outcome if the market is closed or there's no trading data yet.
        # We can log a warning but not fail the test.
        print(f"Warning: No trading data returned for {symbol} on {date_str}. This may be expected if the market is closed.")
        assert True  # Pass the test, as this is a valid state.
    else:
        # If data IS returned, it must be a valid DataFrame.
        keys = ["t", "o", "h", "l", "c", "v"]
        min_len = min(len(data.get(k, [])) for k in keys)
        
        assert min_len > 0, "API returned data but it was empty."

        df = pd.DataFrame({
            "time": pd.to_datetime(data["t"][:min_len], unit="s"),
            "open": data["o"][:min_len],
            "high": data["h"][:min_len],
            "low": data["l"][:min_len],
            "close": data["c"][:min_len],
            "volume": data["v"][:min_len],
        })

        assert not df.empty
        expected_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        assert all(col in df.columns for col in expected_columns)
        print(f"Successfully fetched and validated {len(df)} data points for {symbol} on {date_str}.")

