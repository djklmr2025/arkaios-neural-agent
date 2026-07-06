param(
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$puterHome = Join-Path $repo "puter_home"
$tokenPath = Join-Path $env:LOCALAPPDATA "NeuralAgent\local_bridge_token.txt"
$configPath = Join-Path $puterHome "bridge-config.js"

if (!(Test-Path $puterHome)) {
    throw "No encontre puter_home: $puterHome"
}

if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -eq "python.exe" -and
            $_.CommandLine -like "*http.server 4177*"
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

if (Test-Path $tokenPath) {
    $token = (Get-Content $tokenPath -Raw).Trim()
    $config = @"
window.NEURALAGENT_BRIDGE = {
  url: "http://127.0.0.1:8000/local-bridge",
  token: "$token"
};
"@
    Set-Content -Path $configPath -Value $config -Encoding UTF8
    Write-Host "Bridge token cargado automaticamente desde $tokenPath" -ForegroundColor Green
} else {
    $config = @"
window.NEURALAGENT_BRIDGE = {
  url: "http://127.0.0.1:8000/local-bridge",
  token: ""
};
"@
    Set-Content -Path $configPath -Value $config -Encoding UTF8
    Write-Host "Aun no existe token del bridge. Arranca primero NeuralAgent DEV." -ForegroundColor Yellow
}

Set-Location $puterHome
Write-Host "Puter Home: http://127.0.0.1:4177" -ForegroundColor Green
py -3 -m http.server 4177 --bind 127.0.0.1
