# Stop all Celery-task related services
$stopped = @()

# Get all Python processes
$pythonProcesses = Get-CimInstance Win32_Process -Filter "Name='python.exe'"

foreach ($proc in $pythonProcesses) {
    $cmdLine = $proc.CommandLine
    if ($cmdLine -match 'celery-task' -or $cmdLine -match 'celery.*worker' -or $cmdLine -match 'flower') {
        Write-Host "Stopping PID=$($proc.ProcessId): $cmdLine"
        Stop-Process -Id $proc.ProcessId -Force
        $stopped += $proc.ProcessId
    }
}

Write-Host "`nStopped $($stopped.Count) processes"
if ($stopped.Count -gt 0) {
    Write-Host "Stopped PIDs: $($stopped -join ', ')"
}
