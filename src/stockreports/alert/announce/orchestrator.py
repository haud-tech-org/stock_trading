
# --- Third-Party Imports ---
import pandas as pd

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertResult
from .factory import _AnnouncementAlertFactory
from src.stockreports.alert.common.constants import Approach

class AnnouncementAlertOrchestrator:
    """
    Public orchestrator for announcement alert approaches.
    """
    @staticmethod
    def run(approach: str, symbol: str, master_df: pd.DataFrame) -> AlertResult:
        """
        Runs the specified announcement approach for the given symbol and data.
        Makes a copy of the input DataFrame to avoid mutating the original data.
        """
        alerter = _AnnouncementAlertFactory().get_alerter(approach, symbol)
        return alerter.run(master_df.copy())
