param(
    [switch]$Restart,
    [switch]$OpenPuter,
    [switch]$OpenNeuralAgentDesktop,
    [switch]$SkipPuterHiddenWorker
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

Write-Host "4/5 ARKAIOS invisible Windows worker..." -ForegroundColor Cyan
$workerArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-arkaios-worker.ps1"))
if ($Restart) { $workerArgs += "-Restart" }
& powershell.exe @workerArgs

if (!$SkipPuterHiddenWorker) {
    Write-Host "5/5 ARKAIOS hidden Puter worker..." -ForegroundColor Cyan
    $puterWorkerArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-puter-worker-hidden.ps1"))
    if ($Restart) { $puterWorkerArgs += "-Restart" }
    try {
        & powershell.exe @puterWorkerArgs
        if ($LASTEXITCODE -ne 0) {
            throw "start-puter-worker-hidden.ps1 salio con codigo $LASTEXITCODE"
        }
    } catch {
        Write-Host "Worker Puter local oculto no disponible: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "El core continua. Para modo Puter real usa ARRANCAR_ARKAIOS_ONLINE.bat." -ForegroundColor Yellow
    }
}

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
Write-Host "Hidden Puter worker: channel puter-native"
Write-Host ""
Write-Host "Nota: los workers atienden neuro-login y puter-native aunque la app visual Puter no este abierta."
