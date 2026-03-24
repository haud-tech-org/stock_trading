import argparse
import json
import os
import pandas as pd
from typing import List
import logging

# Add the project root to the Python path
# This is a common pattern to ensure modules can be imported correctly
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
import sys
sys.path.insert(0, project_root)

from src.stockreports.utils.report_utils import find_overall_performance_files, get_report_directory, get_reports_directory_name
from src.stockreports.alert.model.reports_models import ScenarioPerformance, ScenarioRanking, RankedMetric
from src.stockreports.config.validation_settings import DISPLAY_PROFIT_THRESHOLD_AS_DASH


def load_performance_data(report_files: List[str]) -> List[ScenarioPerformance]:
    """
    Loads the 'overall_summary' from each report file into a ScenarioPerformance object.
    """
    all_scenarios: List[ScenarioPerformance] = []
    for file_path in report_files:
        try:
            scenario = ScenarioPerformance.from_file(file_path)
            all_scenarios.append(scenario)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logging.warning(f"Could not process file {file_path}: {e}")
    
    if not all_scenarios:
        raise ValueError("No valid scenario data found in the provided report files.")

    return all_scenarios


def rank_scenarios(scenarios: List[ScenarioPerformance]) -> List[ScenarioRanking]:
    """
    Ranks scenarios based on a prioritized list of metrics.
    """
    num_scenarios = len(scenarios)
    if num_scenarios == 0:
        return []

    # Create DataFrames for easy ranking
    df = pd.DataFrame({
        'profit_threshold': [s.profit_threshold for s in scenarios],
        'loss_threshold': [s.loss_threshold for s in scenarios],
        'profit_per_trade': [s.summary.total_actual_profit_loss / s.summary.total_trades if s.summary.total_trades > 0 else 0 for s in scenarios],
        'total_profit': [s.summary.total_actual_profit_loss for s in scenarios],
        'success_rate': [float(s.summary.success_rate.replace('%','')) for s in scenarios],
        'total_trades': [s.summary.total_trades for s in scenarios],
        'successful_trades': [s.summary.successful_trades for s in scenarios]
    })

    # Rank metrics - higher is better for most, but lower is better for total_trades
    df['profit_per_trade_rank'] = df['profit_per_trade'].rank(ascending=False, method='min').astype(int)
    df['total_profit_rank'] = df['total_profit'].rank(ascending=False, method='min').astype(int)
    df['success_rate_rank'] = df['success_rate'].rank(ascending=False, method='min').astype(int)
    df['total_trades_rank'] = df['total_trades'].rank(ascending=False, method='min').astype(int)
    df['successful_trades_rank'] = df['successful_trades'].rank(ascending=False, method='min').astype(int)

    # Assign scores (1-5). A simple way is to scale ranks.
    # A more nuanced approach could use quintiles, but this is direct.
    max_score = 5
    df['profit_per_trade_score'] = (max_score - (df['profit_per_trade_rank'] - 1) * (max_score - 1) / (num_scenarios - 1 if num_scenarios > 1 else 1)).round().astype(int)
    df['total_profit_score'] = (max_score - (df['total_profit_rank'] - 1) * (max_score - 1) / (num_scenarios - 1 if num_scenarios > 1 else 1)).round().astype(int)
    df['success_rate_score'] = (max_score - (df['success_rate_rank'] - 1) * (max_score - 1) / (num_scenarios - 1 if num_scenarios > 1 else 1)).round().astype(int)
    df['total_trades_score'] = (max_score - (df['total_trades_rank'] - 1) * (max_score - 1) / (num_scenarios - 1 if num_scenarios > 1 else 1)).round().astype(int)
    df['successful_trades_score'] = (max_score - (df['successful_trades_rank'] - 1) * (max_score - 1) / (num_scenarios - 1 if num_scenarios > 1 else 1)).round().astype(int)
    
    # Ensure scores are at least 1
    for col in df.columns:
        if '_score' in col:
            df[col] = df[col].clip(lower=1)

    # Create ScenarioRanking objects
    rankings = []
    for _, row in df.iterrows():
        ranking = ScenarioRanking(
            profit_threshold=row['profit_threshold'],
            loss_threshold=row['loss_threshold'],
            profit_per_trade=RankedMetric(value=row['profit_per_trade'], rank=row['profit_per_trade_rank'], score=row['profit_per_trade_score']),
            total_profit=RankedMetric(value=row['total_profit'], rank=row['total_profit_rank'], score=row['total_profit_score']),
            success_rate=RankedMetric(value=row['success_rate'], rank=row['success_rate_rank'], score=row['success_rate_score']),
            total_trades=RankedMetric(value=row['total_trades'], rank=row['total_trades_rank'], score=row['total_trades_score']),
            successful_trades=RankedMetric(value=row['successful_trades'], rank=row['successful_trades_rank'], score=row['successful_trades_score']),
            total_score=0  # total_score is no longer used for ranking
        )
        rankings.append(ranking)
        
    # Sort by prioritized metrics. Higher scores are better.
    return sorted(
        rankings,
        key=lambda r: (
            r.total_profit.score,
            r.success_rate.score,
            r.successful_trades.score,
            r.profit_per_trade.score,
            r.total_trades.score
        ),
        reverse=False
    )


def generate_markdown_report(scenarios: List[ScenarioPerformance], rankings: List[ScenarioRanking], output_path: str):
    """
    Generates the final markdown report from the analysis.
    """
    if not scenarios or not rankings:
        return

    best_scenario_ranking = rankings[0]
    worst_scenario_ranking = rankings[-1]

    # Find the corresponding ScenarioPerformance objects
    best_scenario_perf = next(s for s in scenarios if s.profit_threshold == best_scenario_ranking.profit_threshold and s.loss_threshold == best_scenario_ranking.loss_threshold)
    worst_scenario_perf = next(s for s in scenarios if s.profit_threshold == worst_scenario_ranking.profit_threshold and s.loss_threshold == worst_scenario_ranking.loss_threshold)

    # Get general info from the first scenario (assuming it's consistent)
    first_scenario = scenarios[0]

    def display_profit_threshold(val):
        return '--' if DISPLAY_PROFIT_THRESHOLD_AS_DASH else val

    with open(output_path, 'w') as f:
        # --- Section 1: High-Level Summary ---
        f.write("# Performance Analysis Summary\n\n")
        f.write(f"**Execution Symbol:** `{best_scenario_perf.execution_symbol}`\n")
        f.write(f"**Source Symbols:** `{', '.join(best_scenario_perf.summary.source_symbols)}`\n")
        f.write(f"**Date Range:** `{best_scenario_perf.start_date}` to `{best_scenario_perf.end_date}`\n\n")
        f.write(f"---Results---\n\n")
        f.write(f"**Best Scenario (Profit/Loss):** `{display_profit_threshold(best_scenario_ranking.profit_threshold)}` / `{best_scenario_ranking.loss_threshold}`\n")
        f.write(f"**Worst Scenario (Profit/Loss):** `{display_profit_threshold(worst_scenario_ranking.profit_threshold)}` / `{worst_scenario_ranking.loss_threshold}`\n\n")

        # --- Section 2: Detailed Summary Table ---
        f.write("## 2. Detailed Scenario Performance\n\n")
        f.write("Ordered by Total P/L\n\n")
        header = "| Scenario (Profit/Loss) | Total Trades | Successful | Failed | Ignored | Success Rate | Total P/L | Best Profit | Worst Loss |\n"
        separator = "|:---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
        f.write(header)
        f.write(separator)
        for s in sorted(scenarios, key=lambda x: x.summary.total_actual_profit_loss, reverse=True):
            summary = s.summary
            row = (f"| `{display_profit_threshold(s.profit_threshold)}/{s.loss_threshold}` | {summary.total_trades} | {summary.successful_trades} | "
                   f"{summary.failed_trades} | {summary.ignored_trades} | {summary.success_rate} | "
                   f"`{summary.total_actual_profit_loss:.2f}` | `{summary.total_best_profit_price:.2f}` | "
                   f"`{summary.total_worst_loss_price:.2f}` |\n")
            f.write(row)
        f.write("\n")

        # --- Section 3: Ranked Performance Analysis ---
        f.write("## 3. Ranked Performance Analysis (Score 1-5, Higher is Better)\n\n")
        f.write("Ordered by Successful Trades\n\n")
        header = ("| Scenario | Profit per Trade | Total Profit | Success Rate | Total Trades (Lower is Better) | Successful Trades |\n")
        separator = "|:---|:---:|:---:|:---:|:---:|:---:|\n"
        f.write(header)
        f.write(separator)

        for r in sorted(rankings, key=lambda x: x.successful_trades.value, reverse=True):
            scenario_name = f"{display_profit_threshold(r.profit_threshold)}/{r.loss_threshold}"
            row = (f"| `{scenario_name}` | "
                   f"`{r.profit_per_trade.value:.2f}` ({r.profit_per_trade.score}) | "
                   f"`{r.total_profit.value:.2f}` ({r.total_profit.score}) | "
                   f"`{r.success_rate.value:.2f}%` ({r.success_rate.score}) | "
                   f"`{int(r.total_trades.value)}` ({r.total_trades.score}) | "
                   f"`{int(r.successful_trades.value)}` ({r.successful_trades.score}) |\n")
            f.write(row)
        f.write("\n")

        # --- Conclusion ---
        f.write("### Conclusion\n\n")
        best_scenario_name = f"{display_profit_threshold(best_scenario_ranking.profit_threshold)}/{best_scenario_ranking.loss_threshold}"
        worst_scenario_name = f"{display_profit_threshold(worst_scenario_ranking.profit_threshold)}/{worst_scenario_ranking.loss_threshold}"
        f.write(f"Based on the prioritized ranking, the **best performing scenario is `{best_scenario_name}`**.\n\n")
        f.write(f"Conversely, the **worst performing scenario is `{worst_scenario_name}`**.\n")

    print(f"Successfully generated performance analysis report at: {output_path}")


def run_analysis(mode: str, base_reports_dir: str):
    """
    Runs the performance analysis and generates a markdown report.
    This function is designed to be called from other scripts.
    """
    reports_base_dir_path = get_report_directory(
        base_dir=base_reports_dir,
        report_type='consolidated',
        mode=mode
    )
    
    report_files = find_overall_performance_files(reports_base_dir_path)
    if not report_files:
        logging.warning(f"No overall performance report files found in {reports_base_dir_path} for analysis.")
        return

    scenarios = load_performance_data(report_files)
    if not scenarios:
        logging.warning("Could not load any valid scenario data for analysis.")
        return
        
    rankings = rank_scenarios(scenarios)
    
    if not rankings:
        logging.warning("No rankings could be generated from the scenario data.")
        return

    # Determine output path dynamically
    first_scenario = scenarios[0]
    start_date = first_scenario.start_date
    end_date = first_scenario.end_date
    symbol = first_scenario.execution_symbol
    
    os.makedirs(reports_base_dir_path, exist_ok=True)
    
    output_filename = f"{symbol}_performance_analysis_{start_date}_to_{end_date}.md"
    output_path = os.path.join(reports_base_dir_path, output_filename)

    generate_markdown_report(scenarios, rankings, output_path)


def main():
    """
    Main function to run the analysis from the command line.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    parser = argparse.ArgumentParser(description="Analyze overall trading performance from report files.")
    parser.add_argument(
        "--base-reports-dir",
        type=str,
        default=None,
        help="The root directory for all reports. If not provided, will use the appropriate directory based on DEBUG_REPLAY_START_TIME."
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="deployment",
        choices=["deployment", "development"],
        help="The execution mode to analyze (deployment or development)."
    )

    args = parser.parse_args()
    
    # If base_reports_dir is not provided, determine it based on the configuration
    if args.base_reports_dir is None:
        reports_dir_name = get_reports_directory_name()
        args.base_reports_dir = os.path.join(project_root, reports_dir_name)
    
    run_analysis(mode=args.mode, base_reports_dir=args.base_reports_dir)


if __name__ == "__main__":
    main()
