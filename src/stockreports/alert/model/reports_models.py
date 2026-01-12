from dataclasses import dataclass
import json
import re
from typing import List

@dataclass
class OverallSummary:
    """
    Represents the 'overall_summary' section of a consolidated performance report.
    """
    total_trades: int
    successful_trades: int
    failed_trades: int
    ignored_trades: int
    success_rate: str
    failure_rate: str
    total_actual_profit_loss: float
    total_best_profit_price: float
    total_worst_loss_price: float
    source_symbols: List[str]  # Added this line


@dataclass
class RankedMetric:
    """Holds the value, rank, and score for a single performance metric."""
    value: float
    rank: int
    score: int


@dataclass
class ScenarioRanking:
    """Represents the complete scored ranking for a single scenario."""
    profit_threshold: float
    loss_threshold: float
    profit_per_trade: RankedMetric
    total_profit: RankedMetric
    success_rate: RankedMetric
    total_trades: RankedMetric
    successful_trades: RankedMetric
    total_score: int


@dataclass
class ScenarioPerformance:
    """
    Represents the performance of a trading scenario.
    """
    profit_threshold: float
    loss_threshold: float
    start_date: str
    end_date: str
    execution_symbol: str
    source_symbols: List[str]
    summary: OverallSummary

    @classmethod
    def from_file(cls, file_path: str):
        with open(file_path, 'r') as f:
            data = json.load(f)

        summary_data = data.get("overall_summary", {})
        
        profit_match = re.search(r"profit_([\d.]+)", file_path)
        loss_match = re.search(r"loss_([\d.]+)", file_path)
        profit = float(profit_match.group(1)) if profit_match else 0.0
        loss = float(loss_match.group(1)) if loss_match else 0.0

        return cls(
            profit_threshold=profit,
            loss_threshold=loss,
            start_date=data.get("start_date", ""),
            end_date=data.get("end_date", ""),
            execution_symbol=data.get("execution_symbol", ""),
            source_symbols=summary_data.get("source_symbols", []),
            summary=OverallSummary(**summary_data)
        )
