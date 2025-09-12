"""
Unit tests for CLI functionality.

Tests the command-line interface commands, argument parsing,
and CLI integration with core functionality.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from io import StringIO
import sys

from stockreports.cli import extract_har_data, aggregate_stock_data, full_pipeline, main


class TestCLICommands:
    """Unit tests for CLI command functions."""
    
    def test_cli_argument_parsing_extract(self):
        """Test extract command argument parsing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            output_dir = Path(temp_dir) / "output"
            source_dir.mkdir()
            
            with patch('sys.argv', ['stockreports-extract', str(source_dir), str(output_dir)]):
                with patch('stockreports.cli.HARExtractor') as mock_extractor:
                    # Setup mocks
                    mock_extractor_instance = MagicMock()
                    mock_extractor_instance.extract_all.return_value = {'entries_extracted': 10, 'files_processed': 2}
                    mock_extractor.return_value = mock_extractor_instance
                    
                    with patch('builtins.print'):
                        with pytest.raises(SystemExit) as exc_info:
                            extract_har_data()
                        
                        # Should exit with success code
                        assert exc_info.value.code == 0
                        
                        # Should call extractor with correct parameters
                        mock_extractor.assert_called_once()
    
    def test_cli_argument_parsing_aggregate(self):
        """Test aggregate command argument parsing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            responses_dir = Path(temp_dir) / "responses"
            output_dir = Path(temp_dir) / "output"
            responses_dir.mkdir()
            
            with patch('sys.argv', ['stockreports-aggregate', str(responses_dir), str(output_dir)]):
                with patch('stockreports.cli.StockDataAggregator') as mock_aggregator:
                    # Setup mocks
                    mock_aggregator_instance = MagicMock()
                    mock_aggregator_instance.process_all_symbols.return_value = {
                        'total_symbols': 2, 'total_records': 100,
                        'VNINDEX': {'trading_days': 10, 'trading_hours_data': 50}
                    }
                    mock_aggregator.return_value = mock_aggregator_instance
                    
                    with patch('builtins.print'):
                        with pytest.raises(SystemExit) as exc_info:
                            aggregate_stock_data()
                        
                        # Should exit with success code
                        assert exc_info.value.code == 0
    
    def test_cli_pipeline_command(self):
        """Test full pipeline command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            har_dir = Path(temp_dir) / "har"
            output_dir = Path(temp_dir) / "output"
            har_dir.mkdir()
            
            with patch('sys.argv', ['stockreports-pipeline', str(har_dir), str(output_dir)]):
                with patch('stockreports.cli.HARExtractor') as mock_extractor:
                    with patch('stockreports.cli.StockDataAggregator') as mock_aggregator:
                        # Setup mocks
                        mock_extractor_instance = MagicMock()
                        mock_extractor_instance.extract_all.return_value = {'entries_extracted': 10, 'files_processed': 2}
                        mock_extractor.return_value = mock_extractor_instance
                        
                        mock_aggregator_instance = MagicMock() 
                        mock_aggregator_instance.process_all_symbols.return_value = {
                            'total_symbols': 2, 'total_records': 100
                        }
                        mock_aggregator.return_value = mock_aggregator_instance
                        
                        with patch('builtins.print'):
                            with pytest.raises(SystemExit) as exc_info:
                                full_pipeline()
                            
                            # Should exit with success code
                            assert exc_info.value.code == 0
    
    def test_cli_main_dispatcher(self):
        """Test main CLI dispatcher."""
        # Test unknown command
        with patch('sys.argv', ['stockreports', 'unknown_command']):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Should exit with error code
                assert exc_info.value.code == 1
                
                # Should print error message
                mock_print.assert_any_call("❌ Unknown command: unknown_command")
    
    def test_cli_no_command(self):
        """Test CLI with no command provided."""
        with patch('sys.argv', ['stockreports']):
            with patch('builtins.print') as mock_print:
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                # Should exit with error code
                assert exc_info.value.code == 1
                
                # Should print usage message
                mock_print.assert_any_call("Usage: stockreports <command> [options]")
    
    def test_cli_extract_nonexistent_directory(self):
        """Test extract command with non-existent source directory."""
        with patch('sys.argv', ['stockreports-extract', 'nonexistent_dir', 'output_dir']):
            with patch('stockreports.cli.Path') as mock_path:
                mock_path.return_value.exists.return_value = False
                
                with patch('builtins.print') as mock_print:
                    with pytest.raises(SystemExit) as exc_info:
                        extract_har_data()
                    
                    # Should exit with error code
                    assert exc_info.value.code == 1
                    
                    # Should print error message
                    mock_print.assert_any_call("❌ Source directory does not exist: nonexistent_dir")
    
    def test_cli_extract_with_verbose(self):
        """Test extract command with verbose flag."""
        with patch('sys.argv', ['stockreports-extract', 'source_dir', 'output_dir', '--verbose']):
            with patch('stockreports.cli.HARExtractor') as mock_extractor:
                with patch('stockreports.cli.Path') as mock_path:
                    # Setup mocks
                    mock_path.return_value.exists.return_value = True
                    mock_extractor_instance = MagicMock()
                    mock_extractor_instance.extract_all.return_value = {'entries_extracted': 0, 'files_processed': 1}
                    mock_extractor.return_value = mock_extractor_instance
                    
                    with patch('builtins.print'):
                        with pytest.raises(SystemExit) as exc_info:
                            extract_har_data()
                        
                        # Should exit with error code for no data
                        assert exc_info.value.code == 1
    
    def test_cli_aggregate_no_symbols(self):
        """Test aggregate command when no symbols found."""
        with patch('sys.argv', ['stockreports-aggregate', 'responses_dir', 'output_dir']):
            with patch('stockreports.cli.StockDataAggregator') as mock_aggregator:
                with patch('stockreports.cli.Path') as mock_path:
                    # Setup mocks
                    mock_path.return_value.exists.return_value = True
                    mock_aggregator_instance = MagicMock()
                    mock_aggregator_instance.process_all_symbols.return_value = {}  # No symbols
                    mock_aggregator.return_value = mock_aggregator_instance
                    
                    with patch('builtins.print') as mock_print:
                        with pytest.raises(SystemExit) as exc_info:
                            aggregate_stock_data()
                        
                        # Should exit with error code
                        assert exc_info.value.code == 1
                        
                        # Should print error message
                        mock_print.assert_any_call("⚠️  No data was aggregated!")
    
    def test_cli_pipeline_extraction_failure(self):
        """Test pipeline when extraction fails."""
        with patch('sys.argv', ['stockreports-pipeline', 'har_dir', 'output_dir']):
            with patch('stockreports.cli.HARExtractor') as mock_extractor:
                with patch('stockreports.cli.Path') as mock_path:
                    # Setup mocks
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.mkdir.return_value = None
                    
                    mock_extractor_instance = MagicMock()
                    mock_extractor_instance.extract_all.return_value = {'entries_extracted': 0, 'files_processed': 1}
                    mock_extractor.return_value = mock_extractor_instance
                    
                    with patch('builtins.print') as mock_print:
                        with pytest.raises(SystemExit) as exc_info:
                            full_pipeline()
                        
                        # Should exit with error code
                        assert exc_info.value.code == 1
                        
                        # Should print error message
                        mock_print.assert_any_call("❌ No data extracted from HAR files!")


class TestCLIIntegration:
    """Integration tests for CLI with core functionality."""
    
    def test_cli_extract_integration(self, tmp_path):
        """Test CLI extract command integration."""
        # Create test HAR file
        har_data = {
            "log": {
                "entries": [{
                    "request": {"url": "https://example.com/api/stock/TEST"},
                    "response": {"content": {"text": json.dumps({"t": ["2025-09-03 09:15:00"], "o": [1500.0]})}}
                }]
            }
        }
        
        har_dir = tmp_path / "har_files"
        har_dir.mkdir()
        har_file = har_dir / "test.har"
        har_file.write_text(json.dumps(har_data))
        
        output_dir = tmp_path / "output"
        
        # Test CLI extract command
        with patch('sys.argv', ['stockreports-extract', str(har_dir), str(output_dir)]):
            with patch('builtins.print'):
                with pytest.raises(SystemExit) as exc_info:
                    extract_har_data()
                
                # Should succeed
                assert exc_info.value.code == 0
                
                # Should create output files
                response_files = list((output_dir / "har_responses").glob("*.json"))
                assert len(response_files) > 0
    
    @pytest.mark.integration
    def test_cli_pipeline_integration(self):
        """Test full CLI pipeline integration with real data."""
        real_har_dir = Path("project/sources/har")
        
        if not real_har_dir.exists():
            pytest.skip("Real HAR files not available")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "pipeline_output"
            
            # Test CLI pipeline command
            with patch('sys.argv', ['stockreports-pipeline', str(real_har_dir), str(output_dir)]):
                with patch('builtins.print'):
                    with pytest.raises(SystemExit) as exc_info:
                        full_pipeline()
                    
                    # Should succeed
                    assert exc_info.value.code == 0
                    
                    # Should create report files
                    reports_dir = output_dir / "reports"
                    if reports_dir.exists():
                        report_files = list(reports_dir.glob("*.md"))
                        assert len(report_files) > 0


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__])
