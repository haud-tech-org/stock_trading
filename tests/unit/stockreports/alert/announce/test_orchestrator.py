
# --- Third-Party Imports ---
import pandas as pd

# --- Project Imports ---
from src.stockreports.alert.announce.orchestrator import AnnouncementAlertOrchestrator
from src.stockreports.alert.common.constants import Approach

def test_price_movement_orchestrator_basic():
    # Create a simple DataFrame with two ticks crossing a level
    df = pd.DataFrame([
        {"close": 99.0},
        {"close": 101.0}
    ], index=["2026-04-25T09:00:00", "2026-04-25T09:01:00"])
    result = AnnouncementAlertOrchestrator.run(
        approach=Approach.PRICE_MOVEMENT,
        symbol="TEST",
        master_df=df
    )
    assert result.approach_name == Approach.PRICE_MOVEMENT
    assert result.status is not None
    assert isinstance(result.confirmed_alerts, list)
