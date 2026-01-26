import pandas as pd
import numpy as np
import json

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
