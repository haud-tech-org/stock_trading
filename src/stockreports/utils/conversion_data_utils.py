import pandas as pd
import numpy as np
import json
from typing import Optional

def make_json_safe(obj):
    """
    Recursively convert objects to JSON-serializable types.
    Handles pandas DataFrame, Series, Timestamp, numpy types, and common containers.
    """
    # Handle pandas DataFrame
    if isinstance(obj, pd.DataFrame):
        records = obj.to_dict(orient="records")
        return [make_json_safe(record) for record in records]
    # Handle pandas Series
    elif isinstance(obj, pd.Series):
        return {k: make_json_safe(v) for k, v in obj.to_dict().items()}
    # Handle pandas Timestamp
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    # Handle dict
    elif isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    # Handle list/tuple/set
    elif isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]
    # Handle numpy types
    if np is not None:
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
    # Fallback: try to convert to string if not natively serializable
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)
    
def default_serializer(obj):
    """
    JSON serializer for objects not serializable by default json code.
    Handles datetime, pandas Timestamp, and falls back to str.
    """
    try:
        if hasattr(obj, 'strftime'):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return str(obj)


# ---------------------------------------------------------------------------
# Primitive type converters
# ---------------------------------------------------------------------------

def to_float(value) -> Optional[float]:
    """
    Safely convert a value to float.
    Returns None if the value is None or cannot be converted.
    Useful for Binance REST responses that return numeric fields as strings.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def to_int(value) -> Optional[int]:
    """
    Safely convert a value to int.
    Returns None if the value is None or cannot be converted.
    Truncates floats (e.g. 1.0 → 1); does NOT round.
    """
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
