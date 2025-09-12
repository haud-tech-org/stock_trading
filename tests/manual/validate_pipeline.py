#!/usr/bin/env python3
"""
Manual validation script for the complete HAR processing pipeline.

This script provides a comprehensive validation of the stockreports pipeline,
similar to the recent successful CLI validation but with additional diagnostics
and flexibility for manual testing and validation.

Usage:
    python tests/manual/validate_pipeline.py [--har-dir HAR_DIR] [--output-dir OUTPUT_DIR]
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

# Add source directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from stockreports.extractors import HARExtractor
    from stockreports.aggregators import StockDataAggregator
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("Please ensure the stockreports package is properly installed")
    sys.exit(1)


def validate_har_files(har_dir):
    """Validate HAR files in directory."""
    print(f"🔍 Validating HAR Files in: {har_dir}")
    print("-" * 50)
    
    har_path = Path(har_dir)
    if not har_path.exists():
        print(f"❌ HAR directory does not exist: {har_dir}")
        return False
    
    har_files = list(har_path.glob("*.har"))
    if not har_files:
        print(f"❌ No HAR files found in: {har_dir}")
        return False
    
    print(f"✅ Found {len(har_files)} HAR files:")
    for har_file in har_files:
        size_mb = har_file.stat().st_size / 1024 / 1024
        print(f"   - {har_file.name} ({size_mb:.1f} MB)")
    
    return True


def run_extraction_phase(har_dir, output_dir):
    """Run HAR extraction phase."""
    print(f"\n🔄 Phase 1: HAR Data Extraction")
    print("=" * 50)
    
    try:
        extractor = HARExtractor(har_dir, output_dir)
        results = extractor.extract_all()
        
        print(f"✅ Extraction Results:")
        print(f"   - Files processed: {results.get('files_processed', 'N/A')}")
        print(f"   - Entries extracted: {results.get('entries_extracted', 'N/A')}")
        
        if hasattr(extractor, 'duplicate_count'):
            print(f"   - Duplicates detected: {extractor.duplicate_count}")
        
        # Validate output structure
        responses_dir = Path(output_dir) / "har_responses"
        if responses_dir.exists():
            response_files = list(responses_dir.glob("*.json"))
            print(f"   - Response files created: {len(response_files)}")
            
            if response_files:
                print(f"   - Sample files:")
                for file_path in response_files[:3]:
                    size_kb = file_path.stat().st_size / 1024
                    print(f"     • {file_path.name} ({size_kb:.1f} KB)")
        
        return results, responses_dir
        
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def run_aggregation_phase(responses_dir, reports_dir):
    """Run data aggregation phase."""
    print(f"\n📊 Phase 2: Data Aggregation and Analysis")
    print("=" * 50)
    
    try:
        aggregator = StockDataAggregator(str(responses_dir), str(reports_dir))
        
        # First, check symbol discovery
        symbols = aggregator.extract_symbols_from_files()
        print(f"🔍 Symbol Discovery:")
        print(f"   - Symbols found: {len(symbols)}")
        if symbols:
            print(f"   - Symbols: {', '.join(symbols)}")
        else:
            print(f"   ❌ No symbols detected!")
            return None
        
        # Run full processing
        results = aggregator.process_all_symbols()
        
        print(f"\n✅ Aggregation Results:")
        total_records = results.get('total_records', 0)
        total_symbols = results.get('total_symbols', 0)
        
        print(f"   - Symbols processed: {total_symbols}")
        print(f"   - Total unique records: {total_records:,}")
        
        # Show detailed results for each symbol
        for symbol, data in results.items():
            if isinstance(data, dict) and 'unique_records' in data:
                print(f"\n   📈 {symbol}:")
                print(f"      - Unique records: {data.get('unique_records', 'N/A')}")
                print(f"      - Files processed: {data.get('files_processed', 'N/A')}")
                print(f"      - Trading days: {data.get('trading_days', 'N/A')}")
                
                if 'timestamp_duplicates' in data:
                    print(f"      - Timestamp duplicates: {data['timestamp_duplicates']}")
                if 'hash_duplicates' in data:
                    print(f"      - Hash duplicates: {data['hash_duplicates']}")
                if 'trading_hours_data' in data:
                    print(f"      - Trading hours data: {data['trading_hours_data']}")
        
        return results
        
    except Exception as e:
        print(f"❌ Aggregation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def validate_outputs(reports_dir):
    """Validate generated output files."""
    print(f"\n📋 Phase 3: Output Validation")
    print("=" * 50)
    
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        print(f"❌ Reports directory does not exist: {reports_dir}")
        return False
    
    report_files = list(reports_path.glob("*.md"))
    if not report_files:
        print(f"❌ No report files found in: {reports_dir}")
        return False
    
    print(f"✅ Generated Reports: {len(report_files)} files")
    
    # Validate report content
    for report_file in report_files:
        size_kb = report_file.stat().st_size / 1024
        content = report_file.read_text()
        
        print(f"\n   📄 {report_file.name} ({size_kb:.1f} KB)")
        
        # Basic content validation
        if len(content) < 100:
            print(f"      ⚠️  Very short content ({len(content)} chars)")
        else:
            print(f"      ✅ Content length: {len(content):,} characters")
        
        if "# " not in content:
            print(f"      ⚠️  No markdown headers found")
        else:
            header_count = content.count("# ")
            print(f"      ✅ Markdown headers: {header_count}")
        
        lines = content.split('\n')
        if len(lines) < 10:
            print(f"      ⚠️  Few lines ({len(lines)})")
        else:
            print(f"      ✅ Lines: {len(lines)}")
        
        # Check for key content indicators
        if any(keyword in content.lower() for keyword in ['trading', 'price', 'volume', 'timestamp']):
            print(f"      ✅ Contains relevant financial data terms")
        else:
            print(f"      ⚠️  May be missing financial data content")
    
    return True


def run_full_validation(har_dir, output_dir):
    """Run complete pipeline validation."""
    print(f"🚀 Starting Full Pipeline Validation")
    print(f"HAR Directory: {har_dir}")
    print(f"Output Directory: {output_dir}")
    print("=" * 70)
    
    # Phase 0: Validate inputs
    if not validate_har_files(har_dir):
        return False
    
    # Phase 1: Extract HAR data
    extraction_results, responses_dir = run_extraction_phase(har_dir, output_dir)
    if not extraction_results:
        return False
    
    # Phase 2: Aggregate data
    reports_dir = Path(output_dir) / "reports"
    aggregation_results = run_aggregation_phase(responses_dir, reports_dir)
    if not aggregation_results:
        return False
    
    # Phase 3: Validate outputs
    if not validate_outputs(reports_dir):
        return False
    
    # Final summary
    print(f"\n🎉 Pipeline Validation Completed Successfully!")
    print("=" * 70)
    print(f"📊 Final Summary:")
    print(f"   - HAR files processed: {extraction_results.get('files_processed', 'N/A')}")
    print(f"   - Total entries: {extraction_results.get('entries_extracted', 'N/A')}")
    print(f"   - Symbols analyzed: {aggregation_results.get('total_symbols', 'N/A')}")
    print(f"   - Unique records: {aggregation_results.get('total_records', 'N/A'):,}")
    print(f"   - Reports generated: {len(list(Path(reports_dir).glob('*.md')))}")
    print(f"   - Output directory: {output_dir}")
    
    return True


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Manual validation of the stockreports pipeline"
    )
    
    parser.add_argument(
        "--har-dir", 
        default="project/sources/har",
        help="Directory containing HAR files (default: project/sources/har)"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory for validation results (default: temporary directory)"
    )
    
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Keep output files after validation (only with --output-dir)"
    )
    
    args = parser.parse_args()
    
    # Use temporary directory if none specified
    if args.output_dir:
        output_dir = args.output_dir
        cleanup_needed = False
    else:
        temp_dir = tempfile.mkdtemp(prefix="stockreports_validation_")
        output_dir = temp_dir
        cleanup_needed = not args.keep_output
        print(f"Using temporary directory: {output_dir}")
    
    try:
        success = run_full_validation(args.har_dir, output_dir)
        
        if success:
            print(f"\n✅ All validation checks passed!")
            if not args.output_dir:
                print(f"📁 Results available in: {output_dir}")
        else:
            print(f"\n❌ Validation failed!")
            return 1
        
    finally:
        if cleanup_needed and not success:
            import shutil
            shutil.rmtree(output_dir, ignore_errors=True)
            print(f"🧹 Cleaned up temporary directory")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
