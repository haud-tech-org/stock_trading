"""
API request utilities for fetching financial data.
"""

import logging
from typing import Any, Dict, Optional

import requests

from src.stockreports.config import loader

settings = loader.get_settings()


def execute_api_request(symbol: str, from_timestamp: int, to_timestamp: int, custom_params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Executes a data request to the API with explicit parameters.

    Args:
        symbol (str): The stock symbol to fetch.
        from_timestamp (int): The start of the time window as a Unix timestamp.
        to_timestamp (int): The end of the time window as a Unix timestamp.
        custom_params (Optional[Dict[str, Any]]): Optional custom parameters to use for the request.

    Returns:
        A dictionary containing the API response data, or None if an error occurs.
    """
    try:
        # Use custom_params if provided, otherwise fall back to default settings
        params = custom_params if custom_params is not None else settings.API_PARAMS.copy()
        
        params.update({
            "symbol": symbol,
            "from": from_timestamp,
            "to": to_timestamp
        })

        response = requests.get(
            settings.API_BASE_URL,
            params=params,
            headers=settings.API_HEADERS,
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        if data.get("s") != "ok" or not data.get("t"):
            logging.warning(f"API returned no data for {symbol}. Status: {data.get('s')}")
            return None

        logging.info(f"Successfully fetched {len(data['t'])} data points for {symbol} from API.")
        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"API request for {symbol} failed: {e}")
        return None
    except (ValueError, KeyError) as e:  # Handles JSON decoding errors or missing keys
        logging.error(f"Error processing API response for {symbol}: {e}")
        return None
