#!/usr/bin/env python3
"""
Stock Technical Analysis Script
Generates comprehensive technical indicator reports for Chinese stocks

This script outputs raw technical indicator data that can be analyzed by LLM.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime


# Import version checker
from version_checker import check_update


def get_venv_python():
    """Get the Python executable path in the virtual environment"""
    skill_root = Path(__file__).parent.parent
    venv_path = skill_root / "venv"

    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "python.exe")
    return str(venv_path / "bin" / "python")


def analyze_stock(stock_input, check_version=True):
    """
    Analyze a stock by code and return raw technical data.

    Args:
        stock_input: Stock code (6 digits)
        check_version: Whether to check for package updates (default: True)

    Returns:
        JSON string containing the technical data or error message
    """
    # Check for package updates (silent, cached)
    version_info = None
    if check_version:
        try:
            version_info = check_update("aishare-txt")
            if version_info.get("has_update"):
                print(f"\n{version_info.get('message', '')}\n", file=sys.stderr)
        except Exception:
            pass  # Silently ignore version check errors

    try:
        from AIShareTxt import StockDataProcessor
    except ImportError:
        return json.dumps({
            "error": "AIShareTxt package not installed or virtual environment not set up.",
            "setup_steps": [
                "1. Install TA-Lib system dependency (see: https://ta-lib.org/install/)",
                "2. Run setup script: python scripts/setup_venv.py",
                "3. Use venv Python: venv/Scripts/python.exe scripts/analyze_stock.py 000001"
            ]
        }, ensure_ascii=False, indent=2)

    # Create processor and generate report
    processor = StockDataProcessor()

    # Validate stock code format (6 digits)
    stock_code = stock_input.strip()
    if not stock_code.isdigit() or len(stock_code) != 6:
        return json.dumps({
            "error": f"Invalid stock code format: '{stock_code}'. Please provide a 6-digit stock code.",
            "example": "000001 (Ping An Bank), 600036 (China Merchants Bank)"
        }, ensure_ascii=False, indent=2)

    try:
        # Get technical report from AIShareTxt
        report = processor.generate_stock_report(stock_code)

        return json.dumps({
            "stock_code": stock_code,
            "report": report,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": f"Failed to analyze stock {stock_code}",
            "message": str(e)
        }, ensure_ascii=False, indent=2)


def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: python analyze_stock.py <stock_code> [--output-dir <path>]",
            "example": "python analyze_stock.py 000001"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    stock_input = sys.argv[1]

    # Parse optional output directory argument
    # Priority: 1. --output-dir argument  2. USER_WORKING_DIR env  3. Current directory
    import os
    output_dir = None

    # Check for --output-dir argument
    if len(sys.argv) >= 4 and sys.argv[2] == "--output-dir":
        output_dir = Path(sys.argv[3])

    # Check USER_WORKING_DIR environment variable
    output_dir_str = os.environ.get("USER_WORKING_DIR", "")
    if output_dir is None and output_dir_str:
        output_dir = Path(output_dir_str)

    # Fallback to current working directory
    if output_dir is None:
        output_dir = Path.cwd()

    # Ensure output directory exists
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(json.dumps({
            "error": f"Cannot create output directory: {output_dir}",
            "message": str(e),
            "hint": "Use --output-dir to specify a valid path"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    result_json = analyze_stock(stock_input)
    result = json.loads(result_json)

    # Print report to console
    if "report" in result:
        print(result["report"])

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Extract trading date from report data (e.g. "数据日期：2026-04-21")
        # Falls back to system date if parsing fails
        date_match = re.search(r'数据日期：(\d{4}-\d{2}-\d{2})', result["report"])
        date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")

        # Save report to: 股票分析报告/YYYY-MM-DD/
        report_dir = output_dir / "股票分析报告" / date_str
        report_dir.mkdir(parents=True, exist_ok=True)
        report_filename = f"stock_report_{stock_input}_{timestamp}.txt"
        report_path = report_dir / report_filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(result["report"])

        # Save JSON to: 股票分析数据/YYYY-MM-DD/
        data_dir = output_dir / "股票分析数据" / date_str
        data_dir.mkdir(parents=True, exist_ok=True)
        json_filename = f"stock_data_{stock_input}_{timestamp}.json"
        json_path = data_dir / json_filename

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(result_json)

        print(f"\n报告已保存: {report_path}", file=sys.stderr)
        print(f"数据已保存: {json_path}", file=sys.stderr)
    else:
        print(result_json)


if __name__ == "__main__":
    main()
