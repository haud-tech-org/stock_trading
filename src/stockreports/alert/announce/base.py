
# --- Standard Library Imports ---
from abc import ABC, abstractmethod

# --- Third-Party Imports ---
import pandas as pd

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertResult

class AnnouncementAlerter(ABC):
    """
    Abstract base class for all announcement alert approaches.
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
