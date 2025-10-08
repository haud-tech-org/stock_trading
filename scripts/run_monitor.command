#!/bin/zsh

# Get the absolute path of the directory where this script is located
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

# The project root is one level up from the scripts directory
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

# The path to the python executable in the virtual environment
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# The path to the monitor script
MONITOR_SCRIPT="$PROJECT_ROOT/src/stockreports/monitoring/realtime_monitor.py"

# Check if the virtual environment and script exist
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Error: Python executable not found in .venv at '$PROJECT_ROOT/.venv'. Please ensure the virtual environment exists."
    exit 1
fi

if [ ! -f "$MONITOR_SCRIPT" ]; then
    echo "Error: Monitor script not found at '$MONITOR_SCRIPT'. Please check the installation."
    exit 1
fi

echo "Starting the stock monitor..."
# Change to the project root directory before running the script
# This ensures that any relative paths inside the python script work correctly
cd "$PROJECT_ROOT" || exit
# Run the monitor script using the virtual environment's python
"$VENV_PYTHON" "$MONITOR_SCRIPT"
