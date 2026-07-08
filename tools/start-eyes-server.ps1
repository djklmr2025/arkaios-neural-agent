param(
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$eyesDir = "C:\ARKAIOS\ELEMIA-v4-arkaios-main\desktop-mcp"
$python = Join-Path $eyesDir "venv\Scripts\python.exe"
$server = Join-Path $eyesDir "eyes_server.py"
$stdout = Join-Path $eyesDir "eyes_stdout.log"
$stderr = Join-Path $eyesDir "eyes_stderr.log"

if (!(Test-Path $python)) {
    throw "No encontre Python del desktop-mcp: $python"
}

if (!(Test-Path $server)) {
    throw "No encontre eyes_server.py: $server"
}

if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -like "python*" -and
            $_.CommandLine -like "*eyes_server.py*"
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

    for ($i = 0; $i -lt 10; $i++) {
        $running = Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -like "python*" -and
                $_.CommandLine -like "*eyes_server.py*"
            }
        if (!$running) { break }
        Start-Sleep -Milliseconds 500
    }
}

if (!(Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue)) {
    Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
    Start-Process -FilePath $python `
        -ArgumentList @("`"$server`"") `
        -WorkingDirectory $eyesDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
}

$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        Invoke-RestMethod "http://127.0.0.1:8001/ping" -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (!$ready) {
    Write-Host "Eyes server no respondio en 20s. Logs:" -ForegroundColor Red
    if (Test-Path $stderr) { Get-Content $stderr -Tail 80 }
    if (Test-Path $stdout) { Get-Content $stdout -Tail 80 }
    exit 1
}

Write-Host "Eyes/Hands server listo: http://127.0.0.1:8001" -ForegroundColor Green
Write-Host "Viewer: http://127.0.0.1:8001/viewer"
