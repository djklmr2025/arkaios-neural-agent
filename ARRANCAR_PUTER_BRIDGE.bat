@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo  NeuralAgent Puter Bridge
echo ==========================================
echo.
echo 1/2 Arrancando backend local y bridge...

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-installed-dev.ps1" -SkipDesktop
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo arrancar el backend/bridge.
    pause
    exit /b 1
)

echo.
echo.
echo 2/3 Arrancando ojos y manos locales...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-eyes-server.ps1" -Restart
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo arrancar ojos/manos locales.
    pause
    exit /b 1
)

echo.
echo 3/3 Arrancando Puter Home...
start "NeuralAgent Puter Home Server" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\serve-puter-home.ps1" -Restart

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:4177"

echo.
echo ==========================================
echo  Listo para probar Puter Home + Bridge
echo ==========================================
echo.
echo Backend local: http://127.0.0.1:8000
echo Ojos/manos: http://127.0.0.1:8001/viewer
echo Puter Home: http://127.0.0.1:4177
echo.
echo Esta version NO abre el .exe viejo para evitar el error de cerebro.
echo.
pause
