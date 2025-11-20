from abc import ABC, abstractmethod
import pandas as pd
from src.stockreports.alert.model.models import AlertResult


class Executor(ABC):
    def __init__(self, symbol: str):
        self.symbol = symbol

    @abstractmethod
    def run(self, df: pd.DataFrame, new_candle_count: int) -> AlertResult:
        pass
