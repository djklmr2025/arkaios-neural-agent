param(
    [switch]$RestartApp,
    [switch]$SkipDesktop
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repo "backend"
$python = Join-Path $backend "venv\Scripts\python.exe"
$server = Join-Path $backend "run_server.py"
$installedExe = Join-Path $env:LOCALAPPDATA "Programs\neuralagent-desktop\neuralagent-desktop.exe"
$stdout = Join-Path $repo "tmp_backend_stdout.log"
$stderr = Join-Path $repo "tmp_backend_stderr.log"

if (!(Test-Path $python)) {
    throw "No encontre Python del venv: $python"
}

if (!$SkipDesktop -and !(Test-Path $installedExe)) {
    throw "No encontre el ejecutable instalado: $installedExe"
}

Get-CimInstance Win32_Process |
    Where-Object { $_.Name -eq "python.exe" -and $_.CommandLine -like "*neuralagentAI-main\backend\run_server.py*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Get-Process -Name "cerebro" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue

Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
Start-Process -FilePath $python `
    -ArgumentList @($server) `
    -WorkingDirectory $backend `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr

$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $response = Invoke-RestMethod "http://127.0.0.1:8000/local-bridge/health" -TimeoutSec 2
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (!$ready) {
    Write-Host "Backend no respondio en 30s. Logs:" -ForegroundColor Red
    if (Test-Path $stderr) { Get-Content $stderr -Tail 80 }
    if (Test-Path $stdout) { Get-Content $stdout -Tail 80 }
    exit 1
}

if (!$SkipDesktop -and $RestartApp) {
    Get-Process -Name "neuralagent-desktop" -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

if (!$SkipDesktop -and !(Get-Process -Name "neuralagent-desktop" -ErrorAction SilentlyContinue)) {
    $oldElectronRunAsNode = $env:ELECTRON_RUN_AS_NODE
    Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
    Start-Process -FilePath $installedExe
    if ($null -ne $oldElectronRunAsNode) {
        $env:ELECTRON_RUN_AS_NODE = $oldElectronRunAsNode
    }
}

if ($SkipDesktop) {
    Write-Host "NeuralAgent backend/bridge listo. Desktop omitido." -ForegroundColor Green
} else {
    Write-Host "NeuralAgent dev instalado listo." -ForegroundColor Green
}
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Bridge token: $env:LOCALAPPDATA\NeuralAgent\local_bridge_token.txt"
Write-Host "Logs:"
Write-Host "  $stdout"
Write-Host "  $stderr"
if ($response) {
    $response | ConvertTo-Json -Depth 4
}
