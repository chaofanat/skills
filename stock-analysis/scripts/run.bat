@echo off
REM Stock Analysis Runner - Windows
REM This script automatically uses the virtual environment Python

setlocal

REM Get the script directory
set "SCRIPT_DIR=%~dp0"
set "SKILL_ROOT=%SCRIPT_DIR%.."
set "VENV_PYTHON=%SKILL_ROOT%\venv\Scripts\python.exe"

REM Check if venv exists
if not exist "%VENV_PYTHON%" (
    echo Virtual environment not found!
    echo Please run: python scripts\setup_venv.py
    exit /b 1
)

REM Check if stock code is provided
if "%~1"=="" (
    echo Usage: run.bat ^<stock_code^>
    echo Example: run.bat 000001
    exit /b 1
)

REM Run the analysis (pass current directory as output directory)
"%VENV_PYTHON%" "%SCRIPT_DIR%analyze_stock.py" %1 --output-dir %CD%
