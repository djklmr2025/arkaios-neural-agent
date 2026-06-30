$ErrorActionPreference = "Continue"
Write-Output "=== Iniciando Verificación de Daemon y Puente Local ===" | Out-File -FilePath verify_output.txt

Write-Output "`n1. Comprobando procesos de Python (posibles colgados):" | Out-File -FilePath verify_output.txt -Append
$pythonProcs = Get-Process python -ErrorAction SilentlyContinue
if ($pythonProcs) {
    $pythonProcs | Select-Object Id, ProcessName, CPU, WorkingSet | Out-File -FilePath verify_output.txt -Append
} else {
    Write-Output "No se encontraron procesos de Python en ejecución." | Out-File -FilePath verify_output.txt -Append
}

Write-Output "`n2. Comprobando puertos locales (Backend 8000, Daemon 8787):" | Out-File -FilePath verify_output.txt -Append
$ports = @(8000, 8787)
foreach ($port in $ports) {
    $conns = netstat -ano | Select-String ":$port "
    if ($conns) {
        Write-Output "Puerto $port está en uso:" | Out-File -FilePath verify_output.txt -Append
        $conns | Out-File -FilePath verify_output.txt -Append
    } else {
        Write-Output "Puerto $port está libre." | Out-File -FilePath verify_output.txt -Append
    }
}

Write-Output "`n3. Verificando ruta del Daemon:" | Out-File -FilePath verify_output.txt -Append
$daemonPath = "$PSScriptRoot\desktop\aiagent\main.py"
if (Test-Path $daemonPath) {
    Write-Output "Paquete daemon encontrado en: $daemonPath" | Out-File -FilePath verify_output.txt -Append
} else {
    Write-Output "No se encontró el paquete daemon en $daemonPath" | Out-File -FilePath verify_output.txt -Append
}

Write-Output "`n=== Fin de Verificación ===" | Out-File -FilePath verify_output.txt -Append
Write-Host "Verificación completada. Resultados guardados en verify_output.txt"
