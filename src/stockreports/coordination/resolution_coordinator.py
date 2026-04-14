"""
ResolutionCoordinator - Maps approaches to their configured resolutions.

Maps each approach to exactly one resolution (1, 5, 15, or 60 minutes).

Pattern: Facade
Responsibility: Single - Provide approach-to-resolution lookups
"""

import logging

from varname import nameof

from src.stockreports.alert.common.constants import Approach
from src.stockreports.config.signal_settings import APPROACH_RESOLUTION_MAPPING
from src.stockreports.config.settings import SYMBOL_ALERT_APPROACHES

logger = logging.getLogger(__name__)


class ResolutionCoordinator:
    """
    Maps trading approaches to their configured resolutions.

    Configuration (APPROACH_RESOLUTION_MAPPING):
        {
            "ICHIMOKU": 15,
            "VRA": 5,
            "CONSISTENT_MOMENTUM": 1,
            "STRONG_CANDLE": 1,
            "VOLUME_SPIKE_CONFIRMATION": 1,
            "CONSISTENT_VOLUME_ANCHOR": 5
        }

    Each approach → exactly one resolution (1, 5, 15, or 60 minutes).

    Example:
        coordinator = ResolutionCoordinator()
        resolution = coordinator.get_resolutions(Approach.ICHIMOKU)  # 15
        resolution = coordinator.get_resolutions(Approach.VRA)       # 5

    Pattern: Facade - Simple interface for approach-to-resolution lookups
    """

    def __init__(self):
        """Initialize from signal settings."""
        try:
            self._config = APPROACH_RESOLUTION_MAPPING
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load {nameof(APPROACH_RESOLUTION_MAPPING)} from signal_settings: {e}")
            raise

        if not self._config:
            logger.error(f"{nameof(APPROACH_RESOLUTION_MAPPING)} is empty or not found!")
            raise ValueError(f"{nameof(APPROACH_RESOLUTION_MAPPING)} must be defined in signal_settings.py")

        self._validate_config()
        logger.info(
            f"Initialized ResolutionCoordinator with {len(self._config)} approach mappings"
        )

    def get_resolutions(self, approach: Approach) -> int:
        """
        Get resolution for an approach.

        Args:
            approach: Approach constant from Approach class (e.g., Approach.ICHIMOKU)

        Returns:
            Resolution in minutes (1, 5, 15, or 60)

        Raises:
            KeyError: If approach not found in APPROACH_RESOLUTION_MAPPING

        Example:
            coordinator.get_resolutions(Approach.ICHIMOKU)  # 15
            coordinator.get_resolutions(Approach.VRA)       # 5
        """
        if approach not in self._config:
            raise KeyError(
                f"Approach '{approach}' not found in {nameof(APPROACH_RESOLUTION_MAPPING)}. "
                f"Available: {list(self._config.keys())}"
            )

        resolution = self._config[approach]
        logger.debug(f"Resolution for {approach}: {resolution}min")
        return resolution

    def get_required_resolutions(self, symbol: str) -> list[int]:
        """
        Get list of required resolutions for a symbol.

        Gets all approaches configured for the symbol from SYMBOL_ALERT_APPROACHES,
        then collects unique resolutions needed for those approaches.

        Args:
            symbol: Stock symbol (e.g., "VN30F1M")

        Returns:
            Sorted list of unique resolutions (integers) needed for this symbol
            Example: [1, 5, 15]

        Example:
            coordinator.get_required_resolutions("VN30F1M")  # [1, 5, 15]
        """
        try:
            # Get approaches configured for this symbol
            symbol_approaches = SYMBOL_ALERT_APPROACHES.get(symbol, [])
            
            if not symbol_approaches:
                logger.warning(f"No approaches configured for symbol {symbol} in {nameof(SYMBOL_ALERT_APPROACHES)}")
                return []

            # Collect unique resolutions for this symbol's approaches
            resolutions = set()
            for approach_name in symbol_approaches:
                try:
                    resolution = self.get_resolutions(approach_name)
                    resolutions.add(resolution)
                except KeyError as e:
                    logger.error(f"Cannot get resolution for approach {approach_name}: {e}")
                    continue

            # Return sorted list
            result = sorted(list(resolutions))
            logger.info(f"Required resolutions for {symbol}: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to get required resolutions for {symbol}: {e}")
            return []

    def _validate_config(self):
        """
        Validate configuration at initialization.

        Checks:
        1. All approaches in APPROACH_RESOLUTION_MAPPING exist in Approach class
        2. All resolutions are numeric integers
        3. All resolutions are in supported set (1, 5, 15, 60)

        Raises:
            ValueError: If any approach doesn't exist in Approach class
            TypeError: If any resolution is not numeric
        """
        if not self._config:
            logger.error(f"{nameof(APPROACH_RESOLUTION_MAPPING)} is empty or not found!")
            raise ValueError(f"{nameof(APPROACH_RESOLUTION_MAPPING)} must be defined in signal_settings.py")

        valid_resolutions = {1, 5, 15, 60}
        # Get all valid approach constants from Approach class
        valid_approaches = Approach.get_all_approaches()

        for approach_name, resolution in self._config.items():
            # Validation 1: Check approach exists in Approach class
            if approach_name not in valid_approaches:
                available = sorted(valid_approaches)
                raise ValueError(
                    f"Approach '{approach_name}' not found in Approach class (from {nameof(APPROACH_RESOLUTION_MAPPING)}). "
                    f"Available: {available}"
                )

            # Validation 2: Check resolution is numeric
            if not isinstance(resolution, int):
                raise TypeError(
                    f"Approach '{approach_name}' resolution must be int, "
                    f"got {type(resolution).__name__}: {resolution}"
                )

            # Validation 3: Check resolution is in supported set
            if resolution not in valid_resolutions:
                raise ValueError(
                    f"Approach '{approach_name}' uses unsupported resolution {resolution}. "
                    f"Supported: {sorted(valid_resolutions)}"
                )

        logger.info(
            f"Configuration validation complete - "
            f"{len(self._config)} approaches validated against Approach class"
        )


# Lazy Singleton Instance
_coordinator_instance = None


def get_coordinator() -> ResolutionCoordinator:
    """
    Get or create ResolutionCoordinator singleton instance (lazy initialization).

    Ensures only one instance is created and reused across the application.
    Configuration validation happens only on first call.

    Returns:
        ResolutionCoordinator singleton instance

    Example:
        coordinator = get_coordinator()
        resolution = coordinator.get_resolutions(Approach.ICHIMOKU)  # 15
    """
    global _coordinator_instance
    
    if _coordinator_instance is None:
        _coordinator_instance = ResolutionCoordinator()
    
    return _coordinator_instance
