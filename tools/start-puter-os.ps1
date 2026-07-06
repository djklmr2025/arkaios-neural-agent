param(
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$puterDir = "C:\ARKAIOS\puter-internetOS"
$nodeHome = "C:\ARKAIOS\.tools\node-v22.23.1-win-x64"
$npm = Join-Path $nodeHome "npm.cmd"
$node = Join-Path $nodeHome "node.exe"
$stdout = Join-Path $puterDir "puter_os_stdout.log"
$stderr = Join-Path $puterDir "puter_os_stderr.log"
$registerArkaios = Join-Path $puterDir "tools\register-arkaios-app.cjs"

if (!(Test-Path $npm)) {
    throw "No encontre npm portable: $npm"
}

if (!(Test-Path $puterDir)) {
    throw "No encontre Puter OS: $puterDir"
}

if ((Test-Path $node) -and (Test-Path $registerArkaios)) {
    & $node $registerArkaios
}

if ($Restart) {
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -like "*puter-internetOS*" -or
            $_.CommandLine -like "*run-selfhosted.js*"
        } |
        ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
}

if (!(Get-NetTCPConnection -LocalPort 4100 -State Listen -ErrorAction SilentlyContinue)) {
    Remove-Item $stdout, $stderr -ErrorAction SilentlyContinue
    $env:Path = "$nodeHome;$env:Path"
    Start-Process -FilePath $npm `
        -ArgumentList @("start") `
        -WorkingDirectory $puterDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $stdout `
        -RedirectStandardError $stderr
}

$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $response = Invoke-WebRequest "http://127.0.0.1:4100" -Headers @{ Host = "puter.localhost:4100" } -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $ready = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (!$ready) {
    Write-Host "Puter OS no respondio aun. Logs:" -ForegroundColor Yellow
    if (Test-Path $stderr) { Get-Content $stderr -Tail 80 }
    if (Test-Path $stdout) { Get-Content $stdout -Tail 80 }
    exit 1
}

Write-Host "Puter OS listo: http://puter.localhost:4100" -ForegroundColor Green
Write-Host "Logs:"
Write-Host "  $stdout"
Write-Host "  $stderr"
