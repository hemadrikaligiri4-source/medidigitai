$port = 8080
# Find all processes listening on the port, excluding PID 0 (System)
$connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -ne 0 }

if ($connections) {
    foreach ($conn in $connections) {
        $targetPid = $conn.OwningProcess
        Write-Host "Found process on port $port with PID $targetPid. Killing it..." -ForegroundColor Yellow
        try {
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
            Write-Host "Successfully killed PID $targetPid." -ForegroundColor Green
        } catch {
            Write-Host "Failed to kill PID $targetPid. You might need to run this as Administrator." -ForegroundColor Red
        }
    }
    Start-Sleep -Seconds 2
} else {
    Write-Host "No active listener found on port $port." -ForegroundColor Green
}

Write-Host "Starting MedDigit Server..." -ForegroundColor Cyan
python app.py
