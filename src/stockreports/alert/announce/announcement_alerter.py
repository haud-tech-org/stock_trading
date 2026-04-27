"""
AnnouncementAlerterBase: Base class for all announcement alert approaches.
Inherits from Alerter and provides the run/execute interface.
"""


# --- Standard Library Imports ---
import logging
from abc import abstractmethod
import pandas as pd

# --- Project Imports ---
from src.stockreports.alert.alerter import Alerter
from src.stockreports.alert.model.models import AlertResult

class AnnouncementAlerterBase(Alerter):
    """
    Base class for all announcement alert approaches (inherits Alerter).
    """
    def run(self, master_df: pd.DataFrame) -> AlertResult:
        """
        Public entry point for running the alert logic. Catches and logs errors.
        """
        try:
            return self.execute(master_df)
        except Exception as e:
            logging.error(f"Error in {self.__class__.__name__}.run: {e}", exc_info=True)
            return AlertResult(
                approach_name=getattr(self, 'APPROACH_NAME', self.__class__.__name__),
                confirmed_alerts=[],
                status=getattr(self, 'Status', None).FAILURE if hasattr(self, 'Status') else 'FAILURE',
                message=f"Exception in run: {e}"
            )

    @abstractmethod
    def execute(self, master_df: pd.DataFrame) -> AlertResult:
        """
        Abstract method to be implemented by each approach.
        """
        pass
