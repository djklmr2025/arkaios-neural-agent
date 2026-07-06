param(
    [switch]$Restart,
    [string]$ChannelId = "neuro-login",
    [string]$BridgeUrl = "http://127.0.0.1:8000/local-bridge"
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repo "backend"
$python = Join-Path $backend "venv\Scripts\python.exe"
$worker = Join-Path $PSScriptRoot "arkaios_worker.py"
$stdout = Join-Path $repo "tmp_arkaios_worker_stdout.log"
$stderr = Join-Path $repo "tmp_arkaios_worker_stderr.log"

if (!(Test-Path $python)) {
    throw "No encontre Python del venv: $python"
}

if (!(Test-Path $worker)) {
    throw "No encontre worker: $worker"
}

if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -like "python*" -and
            $_.CommandLine -like "*arkaios_worker.py*" -and
            $_.CommandLine -like "*$ChannelId*"
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

$running = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -like "python*" -and
        $_.CommandLine -like "*arkaios_worker.py*" -and
        $_.CommandLine -like "*$ChannelId*"
    }

if (!$running) {
    Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
    Start-Process -FilePath $python `
        -ArgumentList @(
            "`"$worker`"",
            "--bridge-url", $BridgeUrl,
            "--channel-id", $ChannelId
        ) `
        -WorkingDirectory $repo `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
}

Start-Sleep -Seconds 1

$running = Get-CimInstance Win32_Process |
    Where-Object {
        $_.Name -like "python*" -and
        $_.CommandLine -like "*arkaios_worker.py*" -and
        $_.CommandLine -like "*$ChannelId*"
    }

if (!$running) {
    Write-Host "ARKAIOS worker no quedo activo. Logs:" -ForegroundColor Red
    if (Test-Path $stderr) { Get-Content $stderr -Tail 80 }
    if (Test-Path $stdout) { Get-Content $stdout -Tail 80 }
    exit 1
}

Write-Host "ARKAIOS worker listo: channel=$ChannelId" -ForegroundColor Green
Write-Host "Logs:"
Write-Host "  $stdout"
Write-Host "  $stderr"
