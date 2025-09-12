"""
Command Line Interface for stockreports package.

This module provides CLI commands for extracting HAR data and aggregating
stock market data with various options for customization.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .extractors import HARExtractor
from .aggregators import StockDataAggregator


def extract_har_data():
    """CLI command for extracting HAR data to JSON responses."""
    parser = argparse.ArgumentParser(
        description='Extract stock market data from HAR files',
        prog='stockreports-extract'
    )
    
    parser.add_argument(
        'source_dir',
        help='Directory containing HAR files to process'
    )
    
    parser.add_argument(
        'output_dir', 
        help='Directory to save extracted JSON responses'
    )
    
    parser.add_argument(
        '--timezone',
        default='Asia/Ho_Chi_Minh',
        help='Timezone for timestamp conversion (default: Asia/Ho_Chi_Minh)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate directories
    source_path = Path(args.source_dir)
    if not source_path.exists():
        print(f"❌ Source directory does not exist: {args.source_dir}")
        sys.exit(1)
    
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create extractor and process
    try:
        extractor = HARExtractor(str(source_path), str(output_path), tz_name=args.timezone)
        results = extractor.extract_all()
        
        if results['entries_extracted'] > 0:
            print(f"✅ Extraction completed successfully!")
            print(f"   - HAR files processed: {results['files_processed']}")
            print(f"   - Responses extracted: {results['entries_extracted']}")
            print(f"   - Output directory: {args.output_dir}")
            sys.exit(0)
        else:
            print("⚠️  No data was extracted from the HAR files!")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def aggregate_stock_data():
    """CLI command for aggregating stock data into reports."""
    parser = argparse.ArgumentParser(
        description='Aggregate stock market data and generate reports',
        prog='stockreports-aggregate'
    )
    
    parser.add_argument(
        'responses_dir',
        help='Directory containing JSON response files'
    )
    
    parser.add_argument(
        'output_dir',
        help='Directory to save aggregated reports'
    )
    
    parser.add_argument(
        '--include-daily-analysis',
        action='store_true',
        help='Include detailed daily price analysis (default: enabled)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate directories
    responses_path = Path(args.responses_dir)
    if not responses_path.exists():
        print(f"❌ Responses directory does not exist: {args.responses_dir}")
        sys.exit(1)
    
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create aggregator and process
    try:
        aggregator = StockDataAggregator(str(responses_path), str(output_path))
        results = aggregator.process_all_symbols()
        
        if results and results.get('total_symbols', 0) > 0:
            print(f"✅ Aggregation completed successfully!")
            print(f"   - Symbols processed: {results['total_symbols']}")
            print(f"   - Total records: {results['total_records']:,}")
            print(f"   - Output directory: {args.output_dir}")
            
            # Show daily analysis summary if available
            for symbol, symbol_data in results.items():
                if isinstance(symbol_data, dict) and 'trading_days' in symbol_data:
                    print(f"   - {symbol}: {symbol_data['trading_days']} trading days, "
                          f"{symbol_data['trading_hours_data']:,} trading hours data points")
        else:
            print("⚠️  No data was aggregated!")
            sys.exit(1)
            
        sys.exit(0)
            
    except Exception as e:
        print(f"❌ Error during aggregation: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def full_pipeline():
    """CLI command for running the complete extraction and aggregation pipeline."""
    parser = argparse.ArgumentParser(
        description='Run complete HAR extraction and stock data aggregation pipeline',
        prog='stockreports-pipeline'
    )
    
    parser.add_argument(
        'har_dir',
        help='Directory containing HAR files to process'
    )
    
    parser.add_argument(
        'output_dir',
        help='Base output directory for all generated files'
    )
    
    parser.add_argument(
        '--timezone',
        default='Asia/Ho_Chi_Minh',
        help='Timezone for timestamp conversion (default: Asia/Ho_Chi_Minh)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--keep-responses',
        action='store_true',
        help='Keep extracted JSON response files after aggregation'
    )
    
    args = parser.parse_args()
    
    # Setup directory structure
    base_output = Path(args.output_dir)
    responses_dir = base_output / 'responses'
    reports_dir = base_output / 'reports'
    
    base_output.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Step 1: Extract HAR data
        print("🔄 Step 1: Extracting HAR data...")
        extractor = HARExtractor(args.har_dir, str(responses_dir), tz_name=args.timezone)
        extraction_results = extractor.extract_all()
        
        if extraction_results['entries_extracted'] == 0:
            print("❌ No data extracted from HAR files!")
            sys.exit(1)
        
        print(f"✅ Extraction completed: {extraction_results['entries_extracted']} responses")
        
        # Step 2: Aggregate data
        print("🔄 Step 2: Aggregating stock data...")
        har_responses_dir = responses_dir / 'har_responses'
        aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
        aggregation_results = aggregator.process_all_symbols()
        
        if not aggregation_results or aggregation_results.get('total_symbols', 0) == 0:
            print("❌ No data aggregated!")
            sys.exit(1)
        
        print(f"✅ Aggregation completed: {aggregation_results['total_symbols']} symbols")
        
        # Cleanup if requested
        if not args.keep_responses:
            import shutil
            shutil.rmtree(responses_dir)
            print("🧹 Cleaned up intermediate response files")
        
        print(f"\n🎉 Pipeline completed successfully!")
        print(f"   - HAR files processed: {extraction_results['files_processed']}")
        print(f"   - Symbols analyzed: {aggregation_results['total_symbols']}")
        print(f"   - Total records: {aggregation_results['total_records']:,}")
        print(f"   - Reports directory: {reports_dir}")
        
        sys.exit(0)
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


def main():
    """Main CLI entry point that dispatches to appropriate command."""
    if len(sys.argv) < 2:
        print("Usage: stockreports <command> [options]")
        print("\nAvailable commands:")
        print("  extract     - Extract data from HAR files") 
        print("  aggregate   - Aggregate stock data into reports")
        print("  pipeline    - Run complete extraction and aggregation")
        print("\nUse 'stockreports <command> --help' for more information.")
        sys.exit(1)
    
    command = sys.argv[1]
    # Remove command from sys.argv so subcommands parse correctly
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    
    if command == 'extract':
        extract_har_data()
    elif command == 'aggregate':
        aggregate_stock_data()
    elif command == 'pipeline':
        full_pipeline()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: extract, aggregate, pipeline")
        sys.exit(1)


if __name__ == "__main__":
    main()
