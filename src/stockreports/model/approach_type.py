
# --- Standard Library Imports ---
from enum import Enum


class ApproachType(str, Enum):
    """
    Enum for approach types in the system.
    """
    TRADE = "trade"
    ANNOUNCE = "announce"
    # Add more types as needed, e.g., 'monitor', 'info', etc.

    @staticmethod
    def from_str(value: str) -> "ApproachType":
        """
        Convert a string to an ApproachType enum value (case-insensitive). Raises ValueError if invalid.
        """
        value_lower = value.lower()
        for item in ApproachType:
            if item.value.lower() == value_lower:
                return item
        raise ValueError(f"Invalid ApproachType: {value}")

    @staticmethod
    def is_valid(value: str) -> bool:
        """
        Check if a string is a valid ApproachType value.
        """
        try:
            ApproachType.from_str(value)
            return True
        except ValueError:
            return False
