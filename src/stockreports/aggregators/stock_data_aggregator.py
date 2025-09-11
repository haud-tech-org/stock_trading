"""
Stock data aggregator for processing multiple symbols from HAR responses.

This module provides a class-based approach to aggregating stock market data
from multiple symbols, detecting columns dynamically, and generating reports.
"""

import os
import json
import hashlib
import re
from collections import defaultdict, Counter
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional, Set

from ..utils.data_utils import (
    get_available_columns,
    get_ordered_columns, 
    validate_data_structure,
    get_column_statistics_map,
    is_trading_hours,
    get_trading_hours_info,
    get_vietnam_timezone_offset,
    TRADING_HOURS,
    TIME_FORMATS
)


class StockDataAggregator:
    """
    Aggregates stock market data from multiple symbols and generates reports.
    
    This class processes HAR response files containing stock market data,
    detects available columns dynamically, removes duplicates, and generates
    comprehensive markdown reports for individual symbols and combined overviews.
    """
    
    def __init__(self, responses_dir: str, output_dir: str):
        """
        Initialize the aggregator with input and output directories.
        
        Args:
            responses_dir: Directory containing HAR response JSON files
            output_dir: Directory where summary reports will be saved
        """
        self.responses_dir = Path(responses_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics mapping for different column types
        self.column_stats_map = get_column_statistics_map()
        
    def extract_symbols_from_files(self) -> List[str]:
        """
        Extract unique symbols from response filenames.
        
        Returns:
            Sorted list of unique symbols found in response files
        """
        symbols: Set[str] = set()
        
        for file_path in self.responses_dir.glob('*.json'):
            filename = file_path.name
            if 'response_' in filename:
                # Extract symbol from filename pattern: {har_source}_response_{idx}_{symbol}.json
                match = re.search(r'response_\d+_([^.]+)\.json$', filename)
                if match:
                    symbol = match.group(1)
                    symbols.add(symbol)
        
        return sorted(list(symbols))
    
    def detect_data_columns(self, sample_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Detect available columns from sample data with validation.
        
        Args:
            sample_data: Sample data structure from JSON response
            
        Returns:
            Dictionary mapping column keys to readable names
        """
        if not sample_data:
            return {}
        
        # Validate data structure first
        is_valid, message = validate_data_structure(sample_data)
        if not is_valid:
            print(f"  ⚠️  Data validation warning: {message}")
        
        # Get available columns using utils
        return get_available_columns(sample_data)
    
    def aggregate_symbol_data(self, symbol: str) -> Tuple[List[Tuple], int, Dict[str, str]]:
        """
        Aggregate data for a specific symbol from all its response files.
        Enhanced with timestamp-based deduplication for the same symbol.
        
        Args:
            symbol: Stock symbol to aggregate data for
            
        Returns:
            Tuple of (unique_rows_data, total_files_processed, detected_columns)
        """
        # Find all response files for this symbol
        pattern = f"*response_*_{symbol}.json"
        files = list(self.responses_dir.glob(pattern))
        
        # Use timestamp-based deduplication for better duplicate detection
        unique_timestamps: Set[str] = set()
        unique_rows: Set[str] = set()
        all_rows: List[Tuple] = []
        detected_columns: Dict[str, str] = {}
        
        print(f"Processing {len(files)} files for symbol: {symbol}")
        
        # Track duplicates for reporting
        total_entries_processed = 0
        timestamp_duplicates = 0
        hash_duplicates = 0
        
        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    resp = json.load(f)
                    
                    # Detect columns from first file
                    if not detected_columns:
                        detected_columns = self.detect_data_columns(resp)
                        print(f"  - Detected columns: {list(detected_columns.keys())}")
                    
                    # Extract data arrays based on detected columns
                    data_arrays = {}
                    for key in detected_columns.keys():
                        data_arrays[key] = resp.get(key, [])
                    
                    # Find minimum length to avoid index errors
                    if data_arrays:
                        min_length = min(len(arr) for arr in data_arrays.values() if arr)
                        
                        for i in range(min_length):
                            total_entries_processed += 1
                            
                            # Create row tuple in consistent order using utils
                            ordered_keys = get_ordered_columns(detected_columns)
                            row_data = []
                            for key in ordered_keys:
                                row_data.append(data_arrays[key][i])
                            
                            # Enhanced duplicate detection using timestamp + symbol
                            timestamp_duplicate = False
                            if 't' in detected_columns and 't' in data_arrays:
                                timestamp = data_arrays['t'][i]
                                if timestamp:
                                    # Create unique identifier: symbol + timestamp
                                    unique_id = f"{symbol}_{timestamp}"
                                    if unique_id in unique_timestamps:
                                        # Skip this record as it's a duplicate timestamp for this symbol
                                        timestamp_duplicates += 1
                                        timestamp_duplicate = True
                                        continue
                                    unique_timestamps.add(unique_id)
                            
                            # Secondary check: full row hash (in case no timestamp or for extra safety)
                            if not timestamp_duplicate:
                                row_tuple = tuple(row_data)
                                row_hash = hashlib.md5(str(row_tuple).encode('utf-8')).hexdigest()
                                
                                if row_hash not in unique_rows:
                                    unique_rows.add(row_hash)
                                    # Store with column info for later use
                                    all_rows.append((row_tuple, detected_columns))
                                else:
                                    hash_duplicates += 1
                                
            except Exception as e:
                print(f"  - Error processing {file_path.name}: {e}")
        
        print(f"  - Total entries processed: {total_entries_processed}")
        print(f"  - Timestamp duplicates removed: {timestamp_duplicates}")
        print(f"  - Hash duplicates removed: {hash_duplicates}")
        print(f"  - Final unique records: {len(all_rows)}")
        return all_rows, len(files), detected_columns
    
    def calculate_symbol_statistics(self, data: List[Tuple], columns: Dict[str, str]) -> Dict[str, Any]:
        """
        Calculate comprehensive statistics for a symbol's data.
        
        Args:
            data: List of data rows for the symbol
            columns: Dictionary of detected columns
            
        Returns:
            Dictionary containing various statistics
        """
        if not data or not columns:
            return {}
        
        # Get ordered column keys using utils
        ordered_keys = get_ordered_columns(columns)
        column_indices = {key: ordered_keys.index(key) for key in ordered_keys}
        
        # Initialize statistics
        stats = {'total_records': len(data)}
        
        # Date range (if time column exists)
        if 't' in columns:
            t_idx = column_indices['t']
            timestamps = [row[0][t_idx] for row in data]
            if timestamps:
                stats['date_range'] = {
                    'start': min(timestamps),
                    'end': max(timestamps)
                }
        
        # Price statistics
        price_stats = {}
        price_columns = self.column_stats_map['price_columns']
        
        for col in price_columns:
            if col in columns:
                col_idx = column_indices[col]
                values = [row[0][col_idx] for row in data 
                         if isinstance(row[0][col_idx], (int, float))]
                if values:
                    if col == 'o':
                        price_stats['avg_open'] = sum(values) / len(values)
                    elif col == 'h':
                        price_stats['max_high'] = max(values)
                    elif col == 'l':
                        price_stats['min_low'] = min(values)
                    elif col == 'c':
                        price_stats['avg_close'] = sum(values) / len(values)
        
        if price_stats:
            stats['price_range'] = price_stats
        
        # Volume statistics
        volume_columns = self.column_stats_map['volume_columns']
        for vol_col in volume_columns:
            if vol_col in columns:
                vol_idx = column_indices[vol_col]
                volumes = [row[0][vol_idx] for row in data 
                          if isinstance(row[0][vol_idx], (int, float))]
                if volumes:
                    stats['volume'] = {
                        'total': sum(volumes),
                        'avg': sum(volumes) / len(volumes),
                        'max': max(volumes)
                    }
                    break  # Use first available volume column
        
        return stats
    
    def calculate_daily_price_analysis(self, data: List[Tuple], columns: Dict[str, str]) -> Dict[str, Any]:
        """
        Perform comprehensive daily price analysis including daily highs/lows and trading patterns.
        
        Args:
            data: List of data rows for the symbol
            columns: Dictionary of detected columns
            
        Returns:
            Dictionary containing daily price analysis
        """
        if not data or not columns:
            return {}
        
        # Get ordered column keys and indices
        ordered_keys = get_ordered_columns(columns)
        column_indices = {key: ordered_keys.index(key) for key in ordered_keys}
        
        # Initialize tracking structures
        daily_lows = defaultdict(lambda: (None, float('inf')))
        daily_highs = defaultdict(lambda: (None, float('-inf')))
        range_counter = Counter()
        trading_hours_data = []
        
        # Check if we have required columns
        if 't' not in columns or 'h' not in columns or 'l' not in columns:
            return {"error": "Missing required columns for daily analysis (t, h, l)"}
        
        t_idx = column_indices['t']
        h_idx = column_indices['h']
        l_idx = column_indices['l']
        
        # Process each data row
        for row in data:
            row_data = row[0]  # Extract tuple from (tuple, columns) format
            
            try:
                # Parse timestamp - handle both epoch and formatted timestamps
                timestamp_str = str(row_data[t_idx])
                if timestamp_str.replace('.', '').isdigit():
                    # Epoch timestamp
                    epoch = float(timestamp_str)
                    dt = datetime.fromtimestamp(epoch) + timedelta(hours=get_vietnam_timezone_offset())  # Convert to VN time
                else:
                    # Already formatted timestamp
                    dt = datetime.strptime(timestamp_str, TIME_FORMATS['datetime_display'])
                    epoch = dt.timestamp()
                
                # Check if within trading hours using utils
                if is_trading_hours(dt.hour, dt.minute):
                    high_price = float(row_data[h_idx])
                    low_price = float(row_data[l_idx])
                    
                    trading_hours_data.append((epoch, low_price, high_price))
                    
                    # Track daily extremes
                    day = dt.strftime('%Y-%m-%d')
                    
                    # Track daily lowest
                    if low_price < daily_lows[day][1]:
                        daily_lows[day] = (epoch, low_price)
                    
                    # Track daily highest
                    if high_price > daily_highs[day][1]:
                        daily_highs[day] = (epoch, high_price)
                    
                    # Count price ranges
                    range_counter[(round(low_price, 2), round(high_price, 2))] += 1
                    
            except (ValueError, IndexError) as e:
                # Skip invalid data points
                continue
        
        # Analyze time patterns
        def format_time_from_epoch(epoch):
            dt = datetime.fromtimestamp(epoch) + timedelta(hours=get_vietnam_timezone_offset())
            return dt.strftime(TIME_FORMATS['time_only'])
        
        # Extract times for pattern analysis
        lowest_times = []
        highest_times = []
        
        for day, (epoch, price) in daily_lows.items():
            if epoch:
                lowest_times.append(format_time_from_epoch(epoch))
        
        for day, (epoch, price) in daily_highs.items():
            if epoch:
                highest_times.append(format_time_from_epoch(epoch))
        
        # Compile analysis results
        analysis_result = {
            'daily_lows': dict(daily_lows),
            'daily_highs': dict(daily_highs),
            'most_repeated_ranges': range_counter.most_common(10),
            'trading_hours_data_count': len(trading_hours_data),
            'total_trading_days': len(daily_lows),
            'lowest_time_patterns': Counter(lowest_times).most_common(5),
            'highest_time_patterns': Counter(highest_times).most_common(5)
        }
        
        # Calculate additional insights
        if daily_lows and daily_highs:
            all_lows = [price for _, price in daily_lows.values() if price != float('inf')]
            all_highs = [price for _, price in daily_highs.values() if price != float('-inf')]
            
            if all_lows and all_highs:
                analysis_result.update({
                    'overall_lowest': min(all_lows),
                    'overall_highest': max(all_highs),
                    'avg_daily_low': sum(all_lows) / len(all_lows),
                    'avg_daily_high': sum(all_highs) / len(all_highs)
                })
        
        return analysis_result
    
    def generate_daily_price_summary(self, symbol: str, data: List[Tuple], 
                                   columns: Dict[str, str], daily_analysis: Dict[str, Any]) -> str:
        """
        Generate detailed daily price summary report.
        
        Args:
            symbol: Stock symbol
            data: Aggregated data
            columns: Detected columns
            daily_analysis: Daily price analysis results
            
        Returns:
            Path to the generated daily summary file
        """
        output_path = self.output_dir / f'{symbol.lower()}_daily_price_summary.md'
        
        if 'error' in daily_analysis:
            # Create minimal report if analysis failed
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f'# {symbol} Daily Price Summary\n\n')
                f.write(f'⚠️ **Error**: {daily_analysis["error"]}\n\n')
                f.write('Required columns for daily analysis: t (time), h (high), l (low)\n')
            return str(output_path)
        
        def format_epoch(epoch):
            dt = datetime.fromtimestamp(epoch) + timedelta(hours=get_vietnam_timezone_offset())
            return dt.strftime(TIME_FORMATS['datetime_display'])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f'# {symbol} Daily Price Summary\n\n')
            
            # Overview section
            f.write('## Trading Overview\n\n')
            f.write(f'- **Total Trading Days**: {daily_analysis.get("total_trading_days", 0)}\n')
            f.write(f'- **Trading Hours Data Points**: {daily_analysis.get("trading_hours_data_count", 0):,}\n')
            
            if 'overall_lowest' in daily_analysis:
                f.write(f'- **Overall Lowest Price**: {daily_analysis["overall_lowest"]:.2f}\n')
                f.write(f'- **Overall Highest Price**: {daily_analysis["overall_highest"]:.2f}\n')
                f.write(f'- **Average Daily Low**: {daily_analysis["avg_daily_low"]:.2f}\n')
                f.write(f'- **Average Daily High**: {daily_analysis["avg_daily_high"]:.2f}\n')
            
            f.write('\n')
            
            # Daily lowest prices
            f.write('## Daily Lowest Prices\n')
            f.write('| Date | Time | Price |\n')
            f.write('|------|------|-------|\n')
            
            daily_lows = daily_analysis.get('daily_lows', {})
            for day in sorted(daily_lows.keys()):
                epoch, price = daily_lows[day]
                if epoch and price != float('inf'):
                    time_str = format_epoch(epoch)
                    f.write(f'| {day} | {time_str} | {price:.2f} |\n')
            
            # Daily highest prices
            f.write('\n## Daily Highest Prices\n')
            f.write('| Date | Time | Price |\n')
            f.write('|------|------|-------|\n')
            
            daily_highs = daily_analysis.get('daily_highs', {})
            for day in sorted(daily_highs.keys()):
                epoch, price = daily_highs[day]
                if epoch and price != float('-inf'):
                    time_str = format_epoch(epoch)
                    f.write(f'| {day} | {time_str} | {price:.2f} |\n')
            
            # Most repeated price ranges
            f.write('\n## Most Repeated Price Ranges\n')
            f.write('| Low | High | Count |\n')
            f.write('|-----|------|-------|\n')
            
            most_repeated = daily_analysis.get('most_repeated_ranges', [])
            for (low, high), count in most_repeated[:10]:
                f.write(f'| {low:.2f} | {high:.2f} | {count} |\n')
            
            # Time pattern analysis
            f.write('\n## Most Common Times for Daily Lowest Prices\n')
            f.write('| Time (HH:MM:SS) | Frequency |\n')
            f.write('|-----------------|----------|\n')
            
            lowest_patterns = daily_analysis.get('lowest_time_patterns', [])
            for time_str, count in lowest_patterns:
                f.write(f'| {time_str} | {count} |\n')
            
            f.write('\n## Most Common Times for Daily Highest Prices\n')
            f.write('| Time (HH:MM:SS) | Frequency |\n')
            f.write('|-----------------|----------|\n')
            
            highest_patterns = daily_analysis.get('highest_time_patterns', [])
            for time_str, count in highest_patterns:
                f.write(f'| {time_str} | {count} |\n')
            
            f.write('\n---\n')
            trading_info = get_trading_hours_info()
            f.write(f'*Analysis includes only data within {trading_info["description"]}*\n')
        
        return str(output_path)
    
    def generate_symbol_summary(self, symbol: str, data: List[Tuple], 
                              stats: Dict[str, Any], columns: Dict[str, str]) -> str:
        """
        Generate markdown summary report for a specific symbol.
        
        Args:
            symbol: Stock symbol
            data: Aggregated data for the symbol
            stats: Calculated statistics
            columns: Detected columns
            
        Returns:
            Path to the generated summary file
        """
        output_path = self.output_dir / f'{symbol.lower()}_summary.md'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f'# {symbol} Stock Data Summary\n\n')
            
            # Statistics section
            f.write('## Summary Statistics\n\n')
            f.write(f'- **Total Records**: {stats["total_records"]:,}\n')
            
            if 'date_range' in stats:
                f.write(f'- **Date Range**: {stats["date_range"]["start"]} to {stats["date_range"]["end"]}\n')
            
            if 'price_range' in stats and stats['price_range']:
                price_stats = stats['price_range']
                if 'min_low' in price_stats and 'max_high' in price_stats:
                    f.write(f'- **Price Range**: {price_stats["min_low"]:.2f} - {price_stats["max_high"]:.2f}\n')
                if 'avg_close' in price_stats:
                    f.write(f'- **Average Close**: {price_stats["avg_close"]:.2f}\n')
            
            if 'volume' in stats:
                vol_stats = stats['volume']
                f.write(f'- **Total Volume**: {vol_stats["total"]:,.0f}\n')
                f.write(f'- **Average Volume**: {vol_stats["avg"]:,.0f}\n')
                f.write(f'- **Max Volume**: {vol_stats["max"]:,.0f}\n')
            
            f.write('\n')
            
            # Dynamic column detection info
            f.write('## Data Columns\n\n')
            f.write('Detected columns in this dataset:\n\n')
            for key, readable_name in columns.items():
                f.write(f'- **{key}**: {readable_name}\n')
            f.write('\n')
            
            # Data table with dynamic columns
            f.write('## Detailed Data\n\n')
            
            # Generate header using ordered columns
            ordered_keys = get_ordered_columns(columns)
            header_row = '| ' + ' | '.join(columns[key] for key in ordered_keys) + ' |\n'
            separator_row = '|' + '|'.join(['--------' for _ in ordered_keys]) + '|\n'
            
            f.write(header_row)
            f.write(separator_row)
            
            # Sort data by timestamp if available
            if 't' in columns:
                t_idx = ordered_keys.index('t')
                sorted_data = sorted(data, key=lambda x: x[0][t_idx])
            else:
                sorted_data = data
            
            # Write data rows
            for row in sorted_data:
                row_data = row[0]  # Extract the tuple from (tuple, columns) format
                formatted_row = '| ' + ' | '.join(str(val) for val in row_data) + ' |\n'
                f.write(formatted_row)
        
        return str(output_path)
    
    def generate_combined_overview(self, all_symbols_data: Dict[str, Tuple]) -> str:
        """
        Generate overview report comparing all symbols.
        
        Args:
            all_symbols_data: Dictionary mapping symbols to their (data, stats, columns)
            
        Returns:
            Path to the generated overview file
        """
        output_path = self.output_dir / 'all_symbols_overview.md'
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('# All Symbols Overview\n\n')
            
            f.write('## Summary by Symbol\n\n')
            f.write('| Symbol | Records | Date Range | Avg Close | Total Volume |\n')
            f.write('|--------|---------|------------|-----------|-------------|\n')
            
            for symbol, (data, stats, columns) in all_symbols_data.items():
                date_range = 'N/A'
                if 'date_range' in stats:
                    date_start = stats["date_range"]["start"]
                    date_end = stats["date_range"]["end"]
                    date_range = f'{date_start} to {date_end}' if date_start != date_end else date_start
                
                avg_close = 'N/A'
                if 'price_range' in stats and 'avg_close' in stats['price_range']:
                    avg_close = f'{stats["price_range"]["avg_close"]:.2f}'
                
                total_volume = 'N/A'
                if 'volume' in stats:
                    total_volume = f'{stats["volume"]["total"]:,.0f}'
                
                f.write(f'| {symbol} | {stats["total_records"]:,} | {date_range} | '
                       f'{avg_close} | {total_volume} |\n')
            
            # Trading activity comparison
            f.write('\n## Trading Activity Comparison\n\n')
            f.write('| Symbol | Available Columns | Min Price | Max Price | Avg Volume |\n')
            f.write('|--------|-------------------|-----------|-----------|------------|\n')
            
            for symbol, (data, stats, columns) in all_symbols_data.items():
                available_cols = ', '.join(get_ordered_columns(columns))
                
                min_price = 'N/A'
                max_price = 'N/A' 
                if 'price_range' in stats:
                    if 'min_low' in stats['price_range']:
                        min_price = f'{stats["price_range"]["min_low"]:.2f}'
                    if 'max_high' in stats['price_range']:
                        max_price = f'{stats["price_range"]["max_high"]:.2f}'
                
                avg_volume = 'N/A'
                if 'volume' in stats:
                    avg_volume = f'{stats["volume"]["avg"]:,.0f}'
                
                f.write(f'| {symbol} | {available_cols} | {min_price} | {max_price} | {avg_volume} |\n')
        
        return str(output_path)
    
    def process_all_symbols(self) -> Dict[str, Dict[str, Any]]:
        """
        Process all symbols and generate comprehensive reports.
        
        Returns:
            Dictionary with processing results and statistics
        """
        print("🔄 Starting multi-symbol stock data aggregation...")
        
        # Extract all symbols from files
        symbols = self.extract_symbols_from_files()
        print(f"📊 Found symbols: {', '.join(symbols)}")
        
        if not symbols:
            print("❌ No symbols found in the response directory!")
            return {}
        
        all_symbols_data = {}
        processing_results = {}
        
        # Process each symbol
        for symbol in symbols:
            print(f"\n📈 Processing symbol: {symbol}")
            
            # Aggregate data for this symbol
            data, total_files, columns = self.aggregate_symbol_data(symbol)
            
            if not data:
                print(f"⚠️  No data found for {symbol}")
                continue
            
            # Calculate statistics
            stats = self.calculate_symbol_statistics(data, columns)
            
            # Perform daily price analysis
            daily_analysis = self.calculate_daily_price_analysis(data, columns)
            
            # Store for combined overview
            all_symbols_data[symbol] = (data, stats, columns)
            
            # Generate individual symbol summary
            summary_path = self.generate_symbol_summary(symbol, data, stats, columns)
            
            # Generate daily price summary
            daily_summary_path = self.generate_daily_price_summary(symbol, data, columns, daily_analysis)
            
            processing_results[symbol] = {
                'unique_records': len(data),
                'total_files': total_files,
                'columns': list(columns.keys()),
                'summary_path': summary_path,
                'daily_summary_path': daily_summary_path,
                'trading_days': daily_analysis.get('total_trading_days', 0),
                'trading_hours_data': daily_analysis.get('trading_hours_data_count', 0)
            }
            
            print(f"✅ Generated {symbol} summary: {len(data)} unique records from {total_files} files")
            print(f"   📋 Columns: {', '.join(columns.keys())}")
            print(f"   📅 Trading days analyzed: {daily_analysis.get('total_trading_days', 0)}")
            print(f"   📊 Trading hours data points: {daily_analysis.get('trading_hours_data_count', 0):,}")
        
        # Generate combined overview
        if all_symbols_data:
            overview_path = self.generate_combined_overview(all_symbols_data)
            print(f"\n📋 Generated combined overview for {len(all_symbols_data)} symbols")
            processing_results['overview_path'] = overview_path
        
        print(f"\n🎉 Aggregation complete! Reports saved to: {self.output_dir}")
        
        # Summary statistics
        total_records = sum(len(data) for data, stats, columns in all_symbols_data.values())
        print(f"📊 Total unique records across all symbols: {total_records:,}")
        
        processing_results['total_records'] = total_records
        processing_results['total_symbols'] = len(all_symbols_data)
        
        return processing_results


def main():
    """Main execution function for standalone usage."""
    import sys
    from pathlib import Path
    
    # Default paths relative to this file
    current_dir = Path(__file__).parent
    responses_dir = current_dir / "../../data/har_responses"
    output_dir = current_dir / "../../data/summary_reports"
    
    # Create aggregator and process
    aggregator = StockDataAggregator(str(responses_dir), str(output_dir))
    results = aggregator.process_all_symbols()
    
    if results:
        print(f"\n✅ Processing completed successfully!")
        print(f"   - Symbols processed: {results.get('total_symbols', 0)}")
        print(f"   - Total records: {results.get('total_records', 0):,}")
    else:
        print("❌ No data was processed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
