# Stock Analysis Runner - Windows PowerShell
# This script automatically uses the virtual environment Python

$ErrorActionPreference = "Stop"

# IMPORTANT: Get original working directory FIRST before any location changes
$OriginalDir = Get-Location

# Get paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillRoot = Split-Path -Parent $ScriptDir
$VenvPython = Join-Path $SkillRoot "venv\Scripts\python.exe"
$AnalyzeScript = Join-Path $ScriptDir "analyze_stock.py"

# Check if venv exists
if (-not (Test-Path $VenvPython)) {
    Write-Host "Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run: python scripts\setup_venv.py" -ForegroundColor Yellow
    exit 1
}

# Check if stock code is provided
if ($args.Count -eq 0) {
    Write-Host "Usage: .\run.ps1 <stock_code>" -ForegroundColor Yellow
    Write-Host "Example: .\run.ps1 000001" -ForegroundColor Yellow
    exit 1
}

$StockCode = $args[0]

# Run the analysis (pass original directory as argument for output)
& $VenvPython $AnalyzeScript $StockCode --output-dir $OriginalDir.Path
