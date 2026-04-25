
# --- Standard Library Imports ---
from typing import Dict, Type

# --- Project Imports ---
from src.stockreports.alert.announce.base import AnnouncementAlerter
from src.stockreports.alert.announce.approach.PRICE_MOVEMENT.alerter import PriceMovementAlerter
from src.stockreports.alert.common.constants import Approach

class _AnnouncementAlertFactory:
    """
    Internal factory for announcement alert approaches (singleton, lazy, cached).
    Uses Approach class constants as the key for approach mapping and cache.
    """
    _instance = None
    _approach_cache: Dict[tuple, AnnouncementAlerter] = {}
    _approach_map: Dict[str, Type[AnnouncementAlerter]] = {
        Approach.PRICE_MOVEMENT: PriceMovementAlerter,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def get_alerter(self, approach: str, symbol: str) -> AnnouncementAlerter:
        key = (approach, symbol)
        if key not in self._approach_cache:
            if approach not in self._approach_map:
                raise ValueError(f"Unknown announcement approach: {approach}")
            self._approach_cache[key] = self._approach_map[approach](symbol)
        return self._approach_cache[key]
