# Lists every non-loopback TCP connection opened by the EventFile app (python) or Ollama
# while it runs. Usage:  powershell -File scripts\watch_connections.ps1 -Seconds 240
param([int]$Seconds = 240)

$seen = @{}
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
    $pids = @(Get-CimInstance Win32_Process |
        Where-Object { ($_.Name -eq "python.exe" -and $_.CommandLine -like "*app.py*") -or $_.Name -eq "ollama.exe" } |
        ForEach-Object { $_.ProcessId })
    Get-NetTCPConnection -ErrorAction SilentlyContinue |
        Where-Object { $pids -contains $_.OwningProcess -and $_.RemoteAddress -notin @("127.0.0.1", "::1", "0.0.0.0", "::") } |
        ForEach-Object {
            $key = "$($_.OwningProcess) $($_.RemoteAddress):$($_.RemotePort)"
            if (-not $seen.ContainsKey($key)) { $seen[$key] = $_.State; "$(Get-Date -Format HH:mm:ss) $key $($_.State)" }
        }
    Start-Sleep -Milliseconds 500
}
"watched $Seconds s; processes: $($pids -join ','); outside connections seen: $($seen.Count)"
