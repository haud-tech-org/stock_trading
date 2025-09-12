"""
Integration tests for the complete HAR processing pipeline.

Tests the full end-to-end pipeline from HAR files to final reports,
including extraction, aggregation, and report generation.
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from stockreports.extractors import HARExtractor
from stockreports.aggregators import StockDataAggregator


class TestFullPipeline:
    """Integration tests for the complete processing pipeline."""
    
    def test_minimal_pipeline_flow(self, tmp_path):
        """Test minimal pipeline with synthetic data."""
        # Create test HAR file
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {"url": "https://example.com/api/stock/VNINDEX"},
                        "response": {
                            "content": {
                                "text": json.dumps({
                                    "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
                                    "o": [1500.0, 1502.0],
                                    "h": [1505.0, 1507.0],
                                    "l": [1498.0, 1500.0],
                                    "c": [1502.0, 1505.0],
                                    "v": [1000, 1200]
                                })
                            }
                        }
                    },
                    {
                        "request": {"url": "https://example.com/api/stock/VN30"},
                        "response": {
                            "content": {
                                "text": json.dumps({
                                    "t": ["2025-09-03 09:25:00", "2025-09-03 09:30:00"],
                                    "o": [800.0, 802.0],
                                    "h": [805.0, 807.0],
                                    "l": [798.0, 800.0],
                                    "c": [802.0, 805.0],
                                    "v": [2000, 2200]
                                })
                            }
                        }
                    }
                ]
            }
        }
        
        # Setup directories
        har_dir = tmp_path / "har_files"
        har_dir.mkdir()
        output_dir = tmp_path / "output"
        reports_dir = tmp_path / "reports"
        
        # Create HAR file
        har_file = har_dir / "test.har"
        har_file.write_text(json.dumps(har_data))
        
        # Step 1: Extract HAR data
        extractor = HARExtractor(str(har_dir), str(output_dir))
        extraction_results = extractor.extract_all()
        
        # Verify extraction
        assert extraction_results["files_processed"] == 1
        assert extraction_results["entries_extracted"] == 2
        
        # Check response files were created
        har_responses_dir = output_dir / "har_responses"
        response_files = list(har_responses_dir.glob("*.json"))
        assert len(response_files) == 2  # VNINDEX and VN30
        
        # Step 2: Aggregate data
        aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
        aggregation_results = aggregator.process_all_symbols()
        
        # Verify aggregation
        assert len(aggregation_results) >= 2  # At least VNINDEX and VN30 data
        assert "VNINDEX" in aggregation_results
        assert "VN30" in aggregation_results
        
        # Step 3: Verify reports were generated
        report_files = list(reports_dir.glob("*.md"))
        assert len(report_files) >= 3  # 2 symbol reports + 1 overview
        
        # Verify report content
        vnindex_reports = [f for f in report_files if "vnindex" in f.name.lower()]
        assert len(vnindex_reports) > 0, "Should generate VNINDEX report"
        
        sample_report = vnindex_reports[0]
        content = sample_report.read_text()
        assert "VNINDEX" in content, "Report should contain symbol name"
        assert len(content) > 100, "Report should have substantial content"
    
    def test_pipeline_with_duplicates(self, tmp_path):
        """Test pipeline handles duplicates correctly across all stages."""
        # Create HAR with duplicate entries
        duplicate_response = {
            "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
            "o": [1500.0, 1502.0],
            "h": [1505.0, 1507.0],
            "l": [1498.0, 1500.0],
            "c": [1502.0, 1505.0],
            "v": [1000, 1200]
        }
        
        har_data = {
            "log": {
                "entries": [
                    {
                        "request": {"url": "https://example.com/api/stock/VNINDEX"},
                        "response": {"content": {"text": json.dumps(duplicate_response)}}
                    },
                    {  # Duplicate response
                        "request": {"url": "https://example.com/api/stock/VNINDEX"},
                        "response": {"content": {"text": json.dumps(duplicate_response)}}
                    }
                ]
            }
        }
        
        # Setup and run pipeline
        har_dir = tmp_path / "har_files"
        har_dir.mkdir()
        har_file = har_dir / "test.har"
        har_file.write_text(json.dumps(har_data))
        
        output_dir = tmp_path / "output"
        reports_dir = tmp_path / "reports"
        
        # Extract
        extractor = HARExtractor(str(har_dir), str(output_dir))
        extraction_results = extractor.extract_all()
        
        # Should detect duplicate during extraction
        assert extractor.duplicate_count == 1
        
        # Aggregate  
        har_responses_dir = output_dir / "har_responses"
        aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
        aggregation_results = aggregator.process_all_symbols()
        
        # Should process successfully despite duplicates
        assert "VNINDEX" in aggregation_results
        vnindex_data = aggregation_results["VNINDEX"]
        assert vnindex_data["unique_records"] >= 1  # At least some data processed
    
    def test_pipeline_error_recovery(self, tmp_path):
        """Test pipeline handles errors gracefully."""
        # Create HAR with some invalid entries
        har_data = {
            "log": {
                "entries": [
                    {  # Valid entry
                        "request": {"url": "https://example.com/api/stock/VNINDEX"},
                        "response": {
                            "content": {
                                "text": json.dumps({
                                    "t": ["2025-09-03 09:15:00"],
                                    "o": [1500.0], "h": [1505.0], "l": [1498.0], "c": [1502.0], "v": [1000]
                                })
                            }
                        }
                    },
                    {  # Invalid JSON in response
                        "request": {"url": "https://example.com/api/stock/VN30"},
                        "response": {"content": {"text": "invalid json"}}
                    },
                    {  # Missing response content
                        "request": {"url": "https://example.com/api/stock/HPG"},
                        "response": {}
                    }
                ]
            }
        }
        
        # Setup and run pipeline
        har_dir = tmp_path / "har_files"
        har_dir.mkdir()
        har_file = har_dir / "test.har"
        har_file.write_text(json.dumps(har_data))
        
        output_dir = tmp_path / "output"
        reports_dir = tmp_path / "reports"
        
        # Should not crash on invalid data
        extractor = HARExtractor(str(har_dir), str(output_dir))
        extraction_results = extractor.extract_all()
        
        # Should process at least the valid entry
        assert extraction_results["entries_extracted"] >= 1
        
        # Aggregation should handle partial data
        har_responses_dir = output_dir / "har_responses"
        if har_responses_dir.exists():
            aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
            aggregation_results = aggregator.process_all_symbols()
            
            # Should return results without crashing
            assert isinstance(aggregation_results, dict)
    
    @pytest.mark.integration
    def test_pipeline_with_real_data(self):
        """Test pipeline with real HAR files if available."""
        real_har_dir = Path("project/sources/har")
        
        if not real_har_dir.exists():
            pytest.skip("Real HAR files not available")
        
        har_files = list(real_har_dir.glob("*.har"))
        if not har_files:
            pytest.skip("No HAR files found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = temp_path / "output"
            reports_dir = temp_path / "reports"
            
            # Run full pipeline
            extractor = HARExtractor(str(real_har_dir), str(output_dir))
            extraction_results = extractor.extract_all()
            
            # Should extract some data
            assert extraction_results["entries_extracted"] > 0
            
            # Run aggregation
            har_responses_dir = output_dir / "har_responses"
            aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
            aggregation_results = aggregator.process_all_symbols()
            
            # Should generate reports
            assert len(aggregation_results) > 0
            
            # Verify report files
            report_files = list(reports_dir.glob("*.md"))
            assert len(report_files) > 0, "Should generate report files"
            
            # Verify report quality
            for report_file in report_files[:2]:  # Check first 2 files
                content = report_file.read_text()
                assert len(content) > 200, f"Report {report_file.name} should have substantial content"
                assert "# " in content, f"Report {report_file.name} should have markdown headers"
                assert content.count("\n") > 10, f"Report {report_file.name} should have multiple lines"
    
    def test_pipeline_performance_characteristics(self, tmp_path):
        """Test pipeline performance with various data sizes."""
        import time
        
        # Create different sized datasets
        test_sizes = [10, 50, 100]  # Number of data points
        
        for size in test_sizes:
            print(f"Testing pipeline with {size} data points...")
            
            # Generate test data
            timestamps = [f"2025-09-03 {9 + i//12:02d}:{(i*5)%60:02d}:00" for i in range(size)]
            values = [1500.0 + i for i in range(size)]
            
            test_data = {
                "t": timestamps,
                "o": values,
                "h": [v + 5 for v in values],
                "l": [v - 5 for v in values],
                "c": [v + 2 for v in values],
                "v": [1000 + i*10 for i in range(size)]
            }
            
            har_data = {
                "log": {
                    "entries": [{
                        "request": {"url": "https://example.com/api/stock/TEST"},
                        "response": {"content": {"text": json.dumps(test_data)}}
                    }]
                }
            }
            
            # Setup test environment
            test_dir = tmp_path / f"test_{size}"
            test_dir.mkdir()
            har_dir = test_dir / "har"
            har_dir.mkdir()
            har_file = har_dir / "test.har"
            har_file.write_text(json.dumps(har_data))
            
            # Time the pipeline
            start_time = time.time()
            
            # Extract
            output_dir = test_dir / "output"
            extractor = HARExtractor(str(har_dir), str(output_dir))
            extraction_results = extractor.extract_all()
            
            # Aggregate
            reports_dir = test_dir / "reports"
            har_responses_dir = output_dir / "har_responses"
            aggregator = StockDataAggregator(str(har_responses_dir), str(reports_dir))
            aggregation_results = aggregator.process_all_symbols()
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            print(f"  Size {size}: {processing_time:.2f}s")
            
            # Verify results
            assert extraction_results["entries_extracted"] == 1
            assert "TEST" in aggregation_results
            
            # Performance should be reasonable (adjust thresholds as needed)
            assert processing_time < 30.0, f"Processing {size} points took too long: {processing_time:.2f}s"


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__])
