$ErrorActionPreference = "SilentlyContinue"

Write-Host "Cleaning up ports 5001 and 5002..."

# Get all processes on port 5001 and 5002
$ports = @(5001, 5002)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port
    foreach ($conn in $connections) {
        if ($conn.OwningProcess) {
            Write-Host "Killing process $($conn.OwningProcess) on port $port"
            Stop-Process -Id $conn.OwningProcess -Force
        }
    }
}

# Kill all python.exe processes just in case
$pythons = Get-Process python
foreach ($p in $pythons) {
    Write-Host "Killing python process $($p.Id)"
    Stop-Process -Id $p.Id -Force
}

Write-Host "Cleanup complete."
