"""
Symbol utilities for standardizing and sanitizing trading symbols.

This module provides helper functions for working with trading symbols across the application.
It handles symbol normalization, sanitization for file paths, and other symbol-related operations.
"""
import re
from typing import Optional


def sanitize_symbol_for_filename(symbol: str) -> str:
    """
    Sanitizes a trading symbol to be safe for use in file and directory names.
    
    Converts problematic characters (/, :, backslash, etc.) to underscores to prevent
    them from being interpreted as path separators.
    
    This is useful for creating consistent, filesystem-safe file paths from
    symbols like "BTC/USDT:USDT" → "BTC_USDT_USDT".
    
    Args:
        symbol (str): The trading symbol to sanitize (e.g., "BTC/USDT:USDT", "VN30F1M").
    
    Returns:
        str: The sanitized symbol safe for use in filenames and paths.
    
    Examples:
        >>> sanitize_symbol_for_filename("BTC/USDT:USDT")
        'BTC_USDT_USDT'
        >>> sanitize_symbol_for_filename("VN30F1M")
        'VN30F1M'
        >>> sanitize_symbol_for_filename("ETH/USDT")
        'ETH_USDT'
    """
    # Replace problematic path separators with underscores
    sanitized = symbol.replace('/', '_').replace(':', '_').replace('\\', '_')
    
    # Optional: Remove any other problematic characters for filesystem safety
    # This regex keeps alphanumeric, underscores, and hyphens
    sanitized = re.sub(r'[^\w\-]', '_', sanitized)
    
    # Remove any leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    # Collapse multiple consecutive underscores to single underscore
    sanitized = re.sub(r'_+', '_', sanitized)
    
    return sanitized


def normalize_symbol(symbol: str) -> str:
    """
    Normalizes a trading symbol to uppercase for consistent comparison and storage.
    
    Args:
        symbol (str): The trading symbol to normalize.
    
    Returns:
        str: The normalized symbol in uppercase.
    
    Examples:
        >>> normalize_symbol("btc/usdt:usdt")
        'BTC/USDT:USDT'
        >>> normalize_symbol("eth/usdt")
        'ETH/USDT'
    """
    return symbol.upper()


def extract_base_symbol(symbol: str) -> str:
    """
    Extracts the base asset from a trading symbol.
    
    Handles common symbol formats:
    - "BTC/USDT:USDT" → "BTC"
    - "BTC/USDT" → "BTC"
    - "VN30F1M" → "VN30F1M" (no standard pair format)
    
    Args:
        symbol (str): The trading symbol.
    
    Returns:
        str: The base asset component of the symbol.
    
    Examples:
        >>> extract_base_symbol("BTC/USDT:USDT")
        'BTC'
        >>> extract_base_symbol("ETH/USDT")
        'ETH'
        >>> extract_base_symbol("VN30F1M")
        'VN30F1M'
    """
    if '/' in symbol:
        return symbol.split('/')[0]
    return symbol


def extract_quote_symbol(symbol: str) -> Optional[str]:
    """
    Extracts the quote asset from a trading symbol.
    
    Handles common symbol formats:
    - "BTC/USDT:USDT" → "USDT"
    - "BTC/USDT" → "USDT"
    - "VN30F1M" → None (no standard pair format)
    
    Args:
        symbol (str): The trading symbol.
    
    Returns:
        str or None: The quote asset component, or None if symbol doesn't have a quote pair.
    
    Examples:
        >>> extract_quote_symbol("BTC/USDT:USDT")
        'USDT'
        >>> extract_quote_symbol("ETH/USDT")
        'USDT'
        >>> extract_quote_symbol("VN30F1M")
        None
    """
    if '/' not in symbol:
        return None
    
    # Handle symbols like "BTC/USDT:USDT" (extract "USDT" from "USDT:USDT")
    quote_part = symbol.split('/')[1]
    if ':' in quote_part:
        return quote_part.split(':')[0]
    return quote_part


def is_perpetual_futures(symbol: str) -> bool:
    """
    Determines if a symbol represents a perpetual futures contract.
    
    Perpetual symbols typically end with ":USDT" or similar.
    
    Args:
        symbol (str): The trading symbol.
    
    Returns:
        bool: True if the symbol appears to be a perpetual futures contract.
    
    Examples:
        >>> is_perpetual_futures("BTC/USDT:USDT")
        True
        >>> is_perpetual_futures("BTC/USDT")
        False
    """
    return ':' in symbol


if __name__ == "__main__":
    # Test examples
    test_symbols = [
        "BTC/USDT:USDT",
        "ETH/USDT",
        "VN30F1M",
        "AAPL/USD",
        "BNB/USDT:USDT"
    ]
    
    print("Symbol Utils Test Examples:")
    print("-" * 80)
    for symbol in test_symbols:
        print(f"\nSymbol: {symbol}")
        print(f"  Sanitized: {sanitize_symbol_for_filename(symbol)}")
        print(f"  Normalized: {normalize_symbol(symbol)}")
        print(f"  Base: {extract_base_symbol(symbol)}")
        print(f"  Quote: {extract_quote_symbol(symbol)}")
        print(f"  Is Perpetual: {is_perpetual_futures(symbol)}")
