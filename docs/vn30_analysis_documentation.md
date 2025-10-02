# Documentation for `vn30_analysis.py`

## 1. Goal of the Script

The primary goal of `vn30_analysis.py` is to perform a comprehensive intraday analysis of 1-minute stock data for the VN30 index. It processes a raw JSON data file, identifies various technical patterns and indicators, and generates a detailed, human-readable summary report in Markdown format (`vn30_analysis_report.md`).

The script is designed to help a new trader understand market behavior by highlighting:
- Significant market turning points (peaks and troughs).
- The duration and strength of price trends.
- Recurring time-based patterns.
- Potential signals for trend reversals.
- Daily volatility and price range.

## 2. Core Implementation

The script executes a pipeline of data processing and analysis steps, which are then compiled into the final report.

### Input and Output
- **Input**: All `.json` files located in the `src/stockreports/data/` directory. The script automatically scans this directory, loads all JSON files, and merges them. Each file is expected to contain timestamped open, high, low, close, and volume data.
- **Output**: A Markdown report file is generated in the root directory. The filename is dynamic and includes a timestamp to prevent overwriting previous reports.
  - If multiple source files are processed, the report is named `combined_analysis_report_[timestamp].md`.
  - If only one source file is used, the report is named `[source_filename]_analysis_report_[timestamp].md`.

### Key Implemented Features

1.  **Data Loading and Preparation**:
    - **Automated Multi-File Loading**: Scans the `src/stockreports/data/` directory and loads all `.json` files found.
    - **Data Merging and Integrity**:
        - Merges data from all files into a single master DataFrame.
        - Sorts the combined data chronologically by timestamp.
        - Removes any duplicate entries based on the timestamp to ensure data integrity.
    - **Timezone Conversion**: Converts all timestamps from UTC to **UTC+7 (Vietnam time)** for local context.

2.  **Significant Pivot Detection**:
    - Instead of a simple 3-point check, the script uses the `scipy.signal.find_peaks` function for robust pivot detection.
    - It identifies significant **tops (peaks)** and **bottoms (troughs)** by analyzing the `high` and `low` prices.
    - The sensitivity is controlled by `prominence` (how much a peak stands out) and `distance` (the minimum separation between peaks), which helps filter out minor market noise and focus on meaningful turning points.

3.  **Consistent Trend Interval Analysis**:
    - The script identifies 5-minute intervals (e.g., 09:00-09:05) that exhibit a consistent trend direction (either always 'up' or always 'down') across all trading days in the dataset.
    - This feature helps pinpoint highly reliable, time-based directional movements.

4.  **Technical Indicators**:
    - **Moving Averages**: Calculates the 5-period (MA5) and 20-period (MA20) moving averages.
    - **MA Crossover Time Zones**: Instead of listing every crossover, the script now analyzes their timing. It identifies the top 5 most frequent 5-minute intervals ('hotspots') for both 'Golden Crosses' and 'Death Crosses', providing traders with actionable time-based insights.
    - **Volume Spike Hotspots**: Similar to crossovers, the script summarizes when volume spikes are most likely to occur. It identifies the top 5 most frequent 5-minute intervals for significant volume activity, helping traders anticipate periods of high market interest.

5.  **Time-Based Pattern Analysis**:
    - **Peak/Trough Time Zones**: Groups pivots into 5-minute intervals to find the most common time zones for market peaks and troughs.

6.  **Intraday Summaries**:
    - **Highest Top and Lowest Bottom**: For each day, it summarizes the absolute highest and lowest price points and notes whether they occurred in the morning or afternoon session.
    - **Intraday Pivot Switches**: Provides a detailed, chronological list of all significant pivots for each day, allowing for an analysis of market rhythm.
    - **Daily Switch Summary**: A sub-section that summarizes, for each day, the total number of pivots and the price range between the highest and lowest pivot, offering a snapshot of daily volatility.
    - **Intraday Peak and Trough Summary**: A table that explicitly shows the single highest peak and lowest trough for each day based on the pivot analysis.

7.  **Advanced Signal Detection**:
    - **Potential Reversal Signals**: The script combines several indicators to find high-probability reversal signals. It looks for a confluence of events: a **pivot** followed by a confirming **MA crossover** and a **volume spike** within a 5-minute window.

8.  **Report Generation**:
    - All the analyses are compiled into a single Markdown file.
    - The report includes a high-level summary, a clickable agenda (Table of Contents), and descriptive explanations for each section to make the data accessible to new traders.
    - It concludes with "Trading Suggestions" that synthesize insights from multiple time-based analyses. It correlates the most frequent times for market tops/bottoms, bullish/bearish MA crossovers, and volume spikes to provide a more comprehensive guide for traders.
