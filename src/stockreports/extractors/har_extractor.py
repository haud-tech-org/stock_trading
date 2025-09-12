"""
HAR Extractor module for processing HTTP Archive files.

This module contains the HARExtractor class for extracting and processing
stock market data from HAR files with Vietnam timezone conversion and
duplicate data record prevention.
"""

import json
import os
import glob
import shutil
import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

from ..utils.data_utils import (
    get_vietnam_timezone_offset,
    TIME_FORMATS,
    VIETNAM_TIMEZONE
)


class HARExtractor:
    """
    Extracts and processes stock market data from HAR (HTTP Archive) files.
    
    Features:
    - Processes multiple HAR files from a directory
    - Converts timestamps to Vietnam timezone (UTC+7)
    - Prevents filename collisions with unique naming
    - Prevents duplicate data records using content hashing
    - Extracts both requests and responses
    - Handles data cleaning and validation
    """
    
    def __init__(self, har_directory: str, output_directory: str = None, tz_name: str = "Asia/Ho_Chi_Minh"):
        """
        Initialize the HAR extractor.
        
        Args:
            har_directory: Path to directory containing HAR files
            output_directory: Path to output directory (optional)
            tz_name: Timezone for timestamp conversion (default: Asia/Ho_Chi_Minh)
        """
        self.har_dir = Path(har_directory)
        
        if output_directory:
            self.output_dir = Path(output_directory)
        else:
            self.output_dir = self.har_dir.parent / "data"
            
        self.requests_dir = self.output_dir / "har_requests"
        self.responses_dir = self.output_dir / "har_responses"
        
        # Vietnam timezone (UTC+7)
        self.vietnam_tz = timezone(timedelta(hours=get_vietnam_timezone_offset()))
        self.timezone_name = tz_name
        
        # Track processed data to prevent duplicates
        self.processed_response_hashes: Set[str] = set()
        self.duplicate_count = 0
        
    def setup_directories(self, clear_existing: bool = True) -> None:
        """
        Setup output directories.
        
        Args:
            clear_existing: Whether to clear existing data directories
        """
        if clear_existing:
            if self.requests_dir.exists():
                shutil.rmtree(self.requests_dir)
            if self.responses_dir.exists():
                shutil.rmtree(self.responses_dir)
        
        self.requests_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)
        
    def find_har_files(self) -> List[Path]:
        """
        Find all HAR files in the source directory.
        
        Returns:
            List of HAR file paths
        """
        return list(self.har_dir.glob('*.har'))
        
    def calculate_response_hash(self, response_data: Dict[str, Any]) -> str:
        """
        Calculate a hash of the response data content to detect duplicates.
        
        Args:
            response_data: Response data dictionary
            
        Returns:
            MD5 hash of the response content
        """
        try:
            # Extract the actual data content, ignoring metadata
            content_to_hash = {}
            
            if isinstance(response_data, dict):
                # For response objects, get the actual data arrays
                for key in ['t', 'o', 'h', 'l', 'c', 'v', 'vw', 'n']:  # Common stock data fields
                    if key in response_data and isinstance(response_data[key], list):
                        content_to_hash[key] = response_data[key]
                        
                # If no standard fields found, hash everything except timestamps
                if not content_to_hash:
                    content_to_hash = {k: v for k, v in response_data.items() 
                                     if k not in ['timestamp', 'time', '_metadata']}
            else:
                content_to_hash = response_data
                
            # Create deterministic hash
            content_str = json.dumps(content_to_hash, sort_keys=True, separators=(',', ':'))
            return hashlib.md5(content_str.encode('utf-8')).hexdigest()
            
        except Exception as e:
            # If hashing fails, create a unique hash to avoid false duplicates
            return hashlib.md5(f"error_{str(response_data)}_{str(e)}".encode('utf-8')).hexdigest()
    
    def is_duplicate_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Check if this response data is a duplicate of previously processed data.
        
        Args:
            response_data: Response data dictionary
            
        Returns:
            True if this is a duplicate, False otherwise
        """
        response_hash = self.calculate_response_hash(response_data)
        
        if response_hash in self.processed_response_hashes:
            self.duplicate_count += 1
            return True
        
        self.processed_response_hashes.add(response_hash)
        return False
    
    def extract_symbol_from_url(self, url: str) -> Optional[str]:
        """
        Extract symbol from URL parameters.
        
        Args:
            url: Request URL
            
        Returns:
            Extracted symbol or None if not found
        """
        # Enhanced pattern matching for different URL formats
        patterns = [
            r'[?&]symbol=([^&]+)',      # ?symbol=VN30
            r'/symbol/([^/?]+)',        # /symbol/VN30
            r'[?&]ticker=([^&]+)',      # ?ticker=VN30
            r'/([A-Z][A-Z0-9]+)(?:[/?]|$)',  # /VN30 or /VNINDEX
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
        
    def convert_to_vietnam_time(self, timestamp_str: str) -> str:
        """
        Convert ISO timestamp to Vietnam time format.
        
        Args:
            timestamp_str: ISO format timestamp string
            
        Returns:
            Formatted timestamp string (YYYY-MM-DD-HH-MM-SS)
        """
        try:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            dt_vietnam = dt.astimezone(self.vietnam_tz)
            return dt_vietnam.strftime(TIME_FORMATS['filename_timestamp'])
        except:
            return f'unknown-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            
    def convert_unix_timestamps(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Unix timestamps in 't' array to Vietnam time format.
        
        Args:
            response_data: Response data dictionary
            
        Returns:
            Modified response data with converted timestamps
        """
        if isinstance(response_data, dict) and 't' in response_data:
            converted_timestamps = []
            for timestamp in response_data['t']:
                try:
                    dt = datetime.fromtimestamp(timestamp, tz=self.vietnam_tz)
                    converted_timestamps.append(dt.strftime(TIME_FORMATS['datetime_display']))
                except:
                    converted_timestamps.append(timestamp)
            response_data['t'] = converted_timestamps
        return response_data
        
    def process_har_file(self, har_file_path: Path) -> Tuple[List[Dict], str]:
        """
        Process a single HAR file.
        
        Args:
            har_file_path: Path to HAR file
            
        Returns:
            Tuple of (entries_list, har_filename)
        """
        har_filename = har_file_path.stem
        
        try:
            with open(har_file_path, 'r', encoding='utf-8') as f:
                har_data = json.load(f)
                
            entries = har_data.get('log', {}).get('entries', [])
            
            # Add HAR filename to each entry for unique naming
            for entry in entries:
                entry['_har_source'] = har_filename
                
            return entries, har_filename
            
        except Exception as e:
            print(f"  - Error processing {har_file_path.name}: {e}")
            return [], har_filename
            
    def save_request(self, request: Dict[str, Any], filename: str) -> None:
        """
        Save request data to file.
        
        Args:
            request: Request data dictionary
            filename: Output filename
        """
        filepath = self.requests_dir / filename
        
        # Remove temporary fields before saving
        request_clean = {k: v for k, v in request.items() if k != '_har_source'}
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(request_clean, f, indent=2)
            
    def save_response(self, response: Dict[str, Any], filename: str) -> None:
        """
        Save response data to file.
        
        Args:
            response: Response data dictionary
            filename: Output filename
        """
        filepath = self.responses_dir / filename
        
        response_content = response.get('content', {}).get('text', None)
        
        if response_content:
            try:
                response_json = json.loads(response_content)
                response_json = self.convert_unix_timestamps(response_json)
            except Exception:
                response_json = response_content
        else:
            response_json = response
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response_json, f, indent=2)
            
    def extract_all(self, clear_existing: bool = True) -> Dict[str, int]:
        """
        Extract data from all HAR files.
        
        Args:
            clear_existing: Whether to clear existing output directories
            
        Returns:
            Dictionary with extraction statistics
        """
        print("🔄 Starting HAR extraction...")
        
        # Setup directories
        self.setup_directories(clear_existing)
        
        # Find HAR files
        har_files = self.find_har_files()
        print(f"📁 Found {len(har_files)} HAR files to process")
        
        if not har_files:
            print("❌ No HAR files found!")
            return {"files_processed": 0, "entries_extracted": 0}
            
        all_entries = []
        files_processed = 0
        
        # Process each HAR file
        for har_file in har_files:
            print(f"📄 Processing: {har_file.name}")
            entries, har_filename = self.process_har_file(har_file)
            
            if entries:
                all_entries.extend(entries)
                files_processed += 1
                print(f"  ✅ Extracted {len(entries)} entries")
            else:
                print(f"  ⚠️  No entries found")
                
        print(f"\n📊 Total entries from all HAR files: {len(all_entries)}")
        print(f"📁 Successfully processed {files_processed} HAR files")
        
        # Process all entries
        self._process_all_entries(all_entries)
        
        print(f"\n🎉 Extraction complete!")
        print(f"📈 Extracted {len(all_entries)} total requests and responses")
        print(f"📂 Output directories:")
        print(f"   - Requests: {self.requests_dir}")
        print(f"   - Responses: {self.responses_dir}")
        
        return {
            "files_processed": files_processed,
            "entries_extracted": len(all_entries)
        }
        
    def _process_all_entries(self, all_entries: List[Dict]) -> None:
        """
        Process all extracted entries and save to files.
        Enhanced with duplicate detection to prevent saving duplicate data.
        
        Args:
            all_entries: List of all HAR entries
        """
        saved_count = 0
        duplicate_count = 0
        
        for idx, entry in enumerate(all_entries):
            request = entry.get('request', {})
            response = entry.get('response', {})
            har_source = entry.get('_har_source', 'unknown')
            
            # Extract symbol from URL
            url = request.get('url', '')
            symbol = self.extract_symbol_from_url(url)
            
            if not symbol:
                continue  # Skip entries without valid symbols
            
            # Parse response content to check for duplicates
            try:
                response_content = response.get('content', {}).get('text', '{}')
                if response_content:
                    response_data = json.loads(response_content)
                    
                    # Check if this response data is a duplicate
                    if self.is_duplicate_response(response_data):
                        duplicate_count += 1
                        print(f"  - Skipping duplicate data for {symbol} (entry {idx+1})")
                        continue
                        
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  - Warning: Could not parse response content for entry {idx+1}: {e}")
                # Continue processing even if we can't check for duplicates
            
            # Generate filenames
            req_filename = f'{har_source}_request_{idx+1}_{symbol}.json'
            res_filename = f'{har_source}_response_{idx+1}_{symbol}.json'
            
            # Save files
            self.save_request(request, req_filename)
            self.save_response(response, res_filename)
            saved_count += 1
        
        print(f"  📊 Processing summary:")
        print(f"     - Entries saved: {saved_count}")
        print(f"     - Duplicates skipped: {duplicate_count}")
        print(f"     - Total processed: {len(all_entries)}")


def main():
    """Main function for standalone execution."""
    import sys
    
    # Default paths (can be overridden via command line)
    har_dir = sys.argv[1] if len(sys.argv) > 1 else "../sources/har"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "../data"
    
    extractor = HARExtractor(har_dir, output_dir)
    stats = extractor.extract_all()
    
    print(f"\n📋 Final Statistics:")
    print(f"   - Files processed: {stats['files_processed']}")
    print(f"   - Entries extracted: {stats['entries_extracted']}")


if __name__ == "__main__":
    main()
