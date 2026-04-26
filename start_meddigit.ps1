# MedDigit Startup Script for PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   MedDigit Server Startup (PowerShell)   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Stop any existing servers on port 5001
$port = 8080
$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -First 1

if ($process) {
    Write-Host "`nStopping existing server (PID: $process)..." -ForegroundColor Yellow
    Stop-Process -Id $process -Force
    Start-Sleep -Seconds 1
}

Write-Host "`nStarting server..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " SERVER IS RUNNING!" -ForegroundColor White
Write-Host " Open this link in your browser:" -ForegroundColor White
Write-Host " http://127.0.0.1:8080" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

python app.py
