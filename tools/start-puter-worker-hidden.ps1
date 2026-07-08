param(
    [switch]$Restart,
    [switch]$OffscreenFallback
)

$ErrorActionPreference = "Stop"

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
$bootstrapUrl = "about:blank"
$workerUrl = "http://puter.localhost:4100/"
$sessionTokenUrl = "http://127.0.0.1:4100/builtin/arkaios/session-token"
$bridgeConfigPath = "C:\ARKAIOS\puter-internetOS\src\arkaios-app\bridge-config.js"
$profileDir = Join-Path $env:LOCALAPPDATA "ARKAIOS\puter-worker-edge-profile"
$debugPort = 9421

if (!(Test-Path $edge)) {
    throw "No encontre Microsoft Edge: $edge"
}

if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -like "msedge*" -and (
                $_.CommandLine -like "*$profileDir*" -or
                $_.CommandLine -like "*remote-debugging-port=$debugPort*" -or
                $_.CommandLine -like "*app/arkaios-worker*"
            )
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }

    Start-Sleep -Seconds 1
}

New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

if (!(Test-Path $bridgeConfigPath)) {
    throw "No encontre bridge-config.js: $bridgeConfigPath"
}

$bridgeConfig = Get-Content -LiteralPath $bridgeConfigPath -Raw
$bridgeTokenMatch = [regex]::Match($bridgeConfig, "bridgeToken:\s*['""]([^'""]+)['""]")
if (!$bridgeTokenMatch.Success) {
    throw "No pude leer bridgeToken desde $bridgeConfigPath"
}
$bridgeToken = $bridgeTokenMatch.Groups[1].Value

try {
    $session = Invoke-RestMethod `
        -Method Post `
        -Uri $sessionTokenUrl `
        -Headers @{ "Host" = "puter.localhost:4100"; "X-ARKAIOS-Bridge-Token" = $bridgeToken } `
        -ContentType "application/json" `
        -Body (@{ username = "arkaios" } | ConvertTo-Json -Compress) `
        -TimeoutSec 5
} catch {
    throw "No pude obtener token local de Puter para el worker oculto: $($_.Exception.Message)"
}

if (!$session.token) {
    throw "Puter no devolvio token de sesion para el worker oculto."
}

$commonArgs = @(
    "--user-data-dir=$profileDir",
    "--remote-debugging-port=$debugPort",
    "--disable-first-run-ui",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--disable-component-extensions-with-background-pages",
    "--disable-background-mode",
    "--disable-session-crashed-bubble",
    "--hide-crash-restore-bubble",
    "--disable-features=Translate,EdgeSigninInterception,msRestoreSessionOnStartup"
)

if ($OffscreenFallback) {
    $args = $commonArgs + @(
        "--new-window",
        "--window-position=-32000,-32000",
        "--window-size=1280,900",
        $bootstrapUrl
    )
} else {
    $args = $commonArgs + @(
        "--headless=new",
        "--disable-gpu",
        "--window-size=1280,900",
        $bootstrapUrl
    )
}

Start-Process -FilePath $edge -ArgumentList $args -WindowStyle Hidden

$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    try {
        Invoke-RestMethod "http://127.0.0.1:$debugPort/json/version" -TimeoutSec 2 | Out-Null
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (!$ready) {
    throw "ARKAIOS Puter worker oculto no expuso DevTools en el puerto $debugPort."
}

$authUrl = "$workerUrl?auth_token=$([System.Uri]::EscapeDataString($session.token))"
$encodedAuthUrl = [System.Uri]::EscapeDataString($authUrl)
try {
    Invoke-RestMethod -Method Put "http://127.0.0.1:$debugPort/json/new?$encodedAuthUrl" -TimeoutSec 5 | Out-Null
} catch {
    try {
        Invoke-RestMethod "http://127.0.0.1:$debugPort/json/new?$encodedAuthUrl" -TimeoutSec 5 | Out-Null
    } catch {
        throw "No pude navegar el worker oculto a Puter autenticado: $($_.Exception.Message)"
    }
}

Write-Host "ARKAIOS Puter worker oculto listo: $workerUrl" -ForegroundColor Green
Write-Host "Modo: $(if ($OffscreenFallback) { 'offscreen' } else { 'headless' })"
