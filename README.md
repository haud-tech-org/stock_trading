# StockReports

A comprehensive Python package for processing stock market data from HTTP Archive (HAR) files.

## Features

- **Multi-HAR Processing**: Extract data from multiple HAR files simultaneously
- **Dynamic Symbol Detection**: Automatically detect and process different stock symbols (VN30, VNINDEX, etc.)
- **Vietnam Timezone Support**: Convert timestamps to Vietnam Time (UTC+7) for local market analysis
- **Dynamic Column Detection**: Adapt to different data structures without hardcoded assumptions
- **Comprehensive Reporting**: Generate detailed markdown reports with statistics and data tables
- **Professional Package Structure**: Modern Python package with proper dependency management

## Installation

### From Source

```bash
git clone <repository-url>
cd stockreports
pip install -e .
```

### Development Installation

```bash
git clone <repository-url>
cd stockreports
pip install -e ".[dev]"
```

## Quick Start

### Python API

```python
from stockreports import HARExtractor, StockDataAggregator

# Extract data from HAR files
extractor = HARExtractor("path/to/har/files", "path/to/output")
results = extractor.extract_all_har_files()

# Generate aggregated reports
aggregator = StockDataAggregator("path/to/responses", "path/to/reports")
aggregator.process_all_symbols()
```

### Command Line Interface

```bash
# Extract HAR data
stockreports extract path/to/har/files path/to/output

# Aggregate stock data  
stockreports aggregate path/to/responses path/to/reports

# Run complete pipeline
stockreports pipeline path/to/har/files path/to/output --timezone Asia/Ho_Chi_Minh
```

## Project Structure

```
src/stockreports/
├── __init__.py           # Main package exports
├── cli.py               # Command line interface
├── extractors/          # HAR file processing
│   ├── __init__.py
│   └── har_extractor.py
├── aggregators/         # Data aggregation and reporting
│   ├── __init__.py
│   └── stock_data_aggregator.py
└── utils/              # Shared utilities
    ├── __init__.py
    └── data_utils.py
```

## Development

### Setup Development Environment

```bash
# Clone and install in development mode
git clone <repository-url>
cd stockreports
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting  
- **flake8**: Linting
- **mypy**: Type checking

Run all checks:

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=stockreports --cov-report=html
```

## Data Flow

1. **HAR Extraction**: Process `.har` files to extract JSON responses containing stock market data
2. **Symbol Detection**: Automatically identify stock symbols (VN30, VNINDEX, etc.) from URLs
3. **Data Aggregation**: Combine data from multiple sources, remove duplicates, detect columns dynamically
4. **Report Generation**: Create comprehensive markdown reports with statistics and data tables

## Configuration

### Timezone Support

The package supports timezone conversion for financial data. Default is Vietnam Time (UTC+7):

```python
extractor = HARExtractor(
    source_dir="path/to/har", 
    output_dir="path/to/output",
    timezone="Asia/Ho_Chi_Minh"  # Default
)
```

### Column Detection

The system automatically detects available columns in your data:

- **Standard Columns**: `t` (time), `o` (open), `h` (high), `l` (low), `c` (close), `v` (volume)
- **Extended Columns**: `vw` (volume weighted), `n` (transactions), `bid`, `ask`, etc.

## Examples

### Processing Multiple Symbols

```python
from stockreports import StockDataAggregator

aggregator = StockDataAggregator("responses/", "reports/")
results = aggregator.process_all_symbols()

print(f"Processed {results['total_symbols']} symbols")
print(f"Total records: {results['total_records']:,}")
```

### Custom Column Handling

```python
from stockreports.utils import get_available_columns, validate_data_structure

# Validate your data structure
is_valid, message = validate_data_structure(your_data)
if is_valid:
    columns = get_available_columns(your_data)
    print(f"Available columns: {list(columns.keys())}")
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and add tests
4. Run the test suite: `pytest`
5. Run code quality checks: `black src/ && flake8 src/`
6. Commit your changes: `git commit -am 'Add feature'`
7. Push to the branch: `git push origin feature-name`
8. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

See [VERSION_HISTORY.md](VERSION_HISTORY.md) for detailed change history and version information.
