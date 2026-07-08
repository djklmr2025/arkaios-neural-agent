@echo off
setlocal

set "ARKAIOS_SCRIPT=%~dp0tools\start-arkaios-online.ps1"

echo.
echo ==========================================
echo  ARKAIOS ONLINE / PUTER REAL
echo ==========================================
echo.
echo Iniciando bridge local, Eyes/Hands y app web ligera.
echo No se inicia Puter OS local.
echo Script: %ARKAIOS_SCRIPT%
echo.

if not exist "%ARKAIOS_SCRIPT%" (
    echo ERROR: No se encontro el script de arranque.
    echo Ruta esperada: %ARKAIOS_SCRIPT%
    echo.
    pause
    exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ARKAIOS_SCRIPT%" -Restart -OpenBrowser
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo arrancar ARKAIOS ONLINE.
    echo.
    pause
    exit /b 1
)

echo.
echo ARKAIOS ONLINE listo.
echo.
if /I "%~1"=="--no-pause" exit /b 0
pause
