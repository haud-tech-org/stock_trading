import pandas as pd
from src.stockreports.config import loader as config_loader

validation_settings = config_loader.get_validation_settings()

def adjust_prices_by_symbol(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Adjusts the price columns of a DataFrame based on the symbol.

    If the symbol is not in the exclusion list, the price columns ('open', 'high', 'low', 'close')
    are divided by 1000.0.

    Args:
        df (pd.DataFrame): The input DataFrame with price data.
        symbol (str): The stock symbol.

    Returns:
        pd.DataFrame: The DataFrame with adjusted prices.
    """
    if symbol not in validation_settings.PRICE_ADJUSTMENT_EXCLUSION_LIST:
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if col in df.columns:
                df[col] = df[col] / 1000.0
    return df
