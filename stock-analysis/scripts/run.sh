#!/bin/bash
# Stock Analysis Runner - Linux/macOS
# This script automatically uses the virtual environment Python

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$SKILL_ROOT/venv/bin/python"

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment not found!"
    echo "Please run: python scripts/setup_venv.py"
    exit 1
fi

# Check if stock code is provided
if [ -z "$1" ]; then
    echo "Usage: ./run.sh <stock_code>"
    echo "Example: ./run.sh 000001"
    exit 1
fi

# Run the analysis (pass current directory as output directory)
"$VENV_PYTHON" "$SCRIPT_DIR/analyze_stock.py" "$1" --output-dir "$(pwd)"
