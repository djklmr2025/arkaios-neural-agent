param(
    [switch]$Restart,
    [switch]$OpenBrowser,
    [switch]$SkipEyes
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$puterHome = Join-Path $repo "puter_home"
$tokenPath = Join-Path $env:LOCALAPPDATA "NeuralAgent\local_bridge_token.txt"
$configPath = Join-Path $puterHome "bridge-config.js"
$stdout = Join-Path $repo "tmp_arkaios_online_stdout.log"
$stderr = Join-Path $repo "tmp_arkaios_online_stderr.log"
$port = 4177
$url = "http://127.0.0.1:$port"

if (!(Test-Path $puterHome)) {
    throw "No encontre ARKAIOS Online Home: $puterHome"
}

Write-Host "== ARKAIOS Online ==" -ForegroundColor Cyan
Write-Host "Runtime: Puter real via https://js.puter.com/v2/ + NeuralAgent Local Bridge" -ForegroundColor Cyan

Write-Host "1/3 NeuralAgent Local Bridge..." -ForegroundColor Cyan
$backendArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-installed-dev.ps1"), "-SkipDesktop")
if ($Restart) { $backendArgs += "-RestartApp" }
& powershell.exe @backendArgs

if (!$SkipEyes) {
    Write-Host "2/3 Eyes/Hands server..." -ForegroundColor Cyan
    $eyesArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "start-eyes-server.ps1"))
    if ($Restart) { $eyesArgs += "-Restart" }
    & powershell.exe @eyesArgs
} else {
    Write-Host "2/3 Eyes/Hands omitido." -ForegroundColor Yellow
}

if (!(Test-Path $tokenPath)) {
    throw "No encontre token del bridge: $tokenPath"
}

$token = (Get-Content -LiteralPath $tokenPath -Raw).Trim()
$config = @"
window.NEURALAGENT_BRIDGE = {
  mode: "online-puter-real",
  url: "http://127.0.0.1:8000/local-bridge",
  token: "$token"
};
"@
Set-Content -Path $configPath -Value $config -Encoding UTF8

Write-Host "3/3 ARKAIOS Online Home..." -ForegroundColor Cyan
if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -like "*http.server $port*"
        } |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

$alreadyRunning = $false
try {
    Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null
    $alreadyRunning = $true
} catch {
    $alreadyRunning = $false
}

if (!$alreadyRunning) {
    Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
    Start-Process -FilePath "py" `
        -ArgumentList @("-3", "-m", "http.server", "$port", "--bind", "127.0.0.1") `
        -WorkingDirectory $puterHome `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
}

$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (!$ready) {
    Write-Host "ARKAIOS Online no respondio en $url. Logs:" -ForegroundColor Red
    if (Test-Path $stderr) { Get-Content $stderr -Tail 80 }
    if (Test-Path $stdout) { Get-Content $stdout -Tail 80 }
    exit 1
}

if ($OpenBrowser) {
    Start-Process $url
}

Write-Host ""
Write-Host "ARKAIOS Online listo." -ForegroundColor Green
Write-Host "App: $url"
Write-Host "Bridge: http://127.0.0.1:8000/local-bridge"
Write-Host "Eyes/Hands: http://127.0.0.1:8001"
Write-Host "Puter: real/nube via https://js.puter.com/v2/"
Write-Host ""
Write-Host "Este modo NO arranca C:\ARKAIOS\puter-internetOS."
