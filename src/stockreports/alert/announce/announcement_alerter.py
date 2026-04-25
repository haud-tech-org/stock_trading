"""
AnnouncementAlerterBase: Base class for all announcement alert approaches.
Inherits from Alerter and provides the run/execute interface.
"""

# --- Standard Library Imports ---
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
        Public entry point for running the alert logic.
        """
        return self.execute(master_df)

    @abstractmethod
    def execute(self, master_df: pd.DataFrame) -> AlertResult:
        """
        Abstract method to be implemented by each approach.
        """
        pass
