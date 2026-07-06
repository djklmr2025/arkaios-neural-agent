param(
    [switch]$Restart,
    [switch]$OpenPuter,
    [switch]$OpenNeuralAgentDesktop
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$puterUrl = "http://puter.localhost:4100/app/arkaios"

Write-Host "== ARKAIOS Core ==" -ForegroundColor Cyan

Write-Host "1/3 Backend + Local Bridge..." -ForegroundColor Cyan
$backendArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-installed-dev.ps1"))
if ($Restart) { $backendArgs += "-RestartApp" }
if (!$OpenNeuralAgentDesktop) { $backendArgs += "-SkipDesktop" }
& powershell.exe @backendArgs

Write-Host "2/3 Eyes/Hands server..." -ForegroundColor Cyan
$eyesArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-eyes-server.ps1"))
if ($Restart) { $eyesArgs += "-Restart" }
& powershell.exe @eyesArgs

Write-Host "3/4 Puter OS server..." -ForegroundColor Cyan
$puterArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-puter-os.ps1"))
if ($Restart) { $puterArgs += "-Restart" }
& powershell.exe @puterArgs

Write-Host "4/4 ARKAIOS invisible worker..." -ForegroundColor Cyan
$workerArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-arkaios-worker.ps1"))
if ($Restart) { $workerArgs += "-Restart" }
& powershell.exe @workerArgs

if ($OpenPuter) {
    Start-Process $puterUrl
}

Write-Host ""
Write-Host "ARKAIOS Core listo." -ForegroundColor Green
Write-Host "Bridge: http://127.0.0.1:8000/local-bridge"
Write-Host "Eyes/Hands: http://127.0.0.1:8001"
Write-Host "Puter OS: http://puter.localhost:4100"
Write-Host "ARKAIOS App: $puterUrl"
Write-Host "Invisible worker: channel neuro-login"
Write-Host ""
Write-Host "Nota: el worker atiende neuro-login aunque la app visual Puter no este abierta."
