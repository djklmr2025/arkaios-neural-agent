@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo  ARKAIOS NUCLEO
echo ==========================================
echo.
echo Arranca backend, bridge local, ojos/manos y Puter OS.
echo Por defecto no abre NeuralAgent Desktop.
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-arkaios-core.ps1" -Restart -OpenPuter
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo arrancar ARKAIOS NUCLEO.
    pause
    exit /b 1
)

echo.
echo Listo. Puedes cerrar esta ventana si ya termino el arranque.
echo.
pause
