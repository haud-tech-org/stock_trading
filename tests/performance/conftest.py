"""
Configuration for performance tests.

Provides fixtures and utilities for performance testing of the stockreports package.
"""

import pytest
import time
import psutil
import os
from pathlib import Path


@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during test execution."""
    process = psutil.Process(os.getpid())
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.end_time = None
            self.end_memory = None
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        def stop(self):
            self.end_time = time.time()
            self.end_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        @property
        def duration(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None
        
        @property
        def memory_usage(self):
            if self.start_memory and self.end_memory:
                return self.end_memory - self.start_memory
            return None
        
        @property
        def peak_memory(self):
            if self.end_memory:
                return self.end_memory
            return None
    
    return PerformanceMonitor()


@pytest.fixture(params=[10, 50, 100, 500])
def dataset_sizes(request):
    """Provide different dataset sizes for performance testing."""
    return request.param


@pytest.fixture
def large_har_data():
    """Generate large HAR data for performance testing."""
    def generate_data(num_entries=1000, num_data_points=100):
        entries = []
        
        for i in range(num_entries):
            symbol = f"STOCK{i % 10}"  # 10 different symbols
            
            # Generate time series data
            timestamps = [f"2025-09-03 {9 + j//12:02d}:{(j*5)%60:02d}:00" for j in range(num_data_points)]
            base_price = 1000 + (i % 100) * 10
            
            data = {
                "t": timestamps,
                "o": [base_price + j for j in range(num_data_points)],
                "h": [base_price + j + 5 for j in range(num_data_points)],
                "l": [base_price + j - 5 for j in range(num_data_points)],
                "c": [base_price + j + 2 for j in range(num_data_points)],
                "v": [1000 + j * 10 for j in range(num_data_points)]
            }
            
            entries.append({
                "request": {"url": f"https://example.com/api/stock/{symbol}"},
                "response": {"content": {"text": json.dumps(data)}}
            })
        
        return {"log": {"entries": entries}}
    
    return generate_data


# Performance test thresholds
PERFORMANCE_THRESHOLDS = {
    "small_dataset": {
        "max_time": 5.0,      # seconds
        "max_memory": 100,    # MB
    },
    "medium_dataset": {
        "max_time": 30.0,     # seconds  
        "max_memory": 500,    # MB
    },
    "large_dataset": {
        "max_time": 120.0,    # seconds
        "max_memory": 1000,   # MB
    }
}
