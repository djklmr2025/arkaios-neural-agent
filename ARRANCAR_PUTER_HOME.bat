@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==============================
echo  NeuralAgent Puter Home
echo ==============================
echo.
echo Abre en tu navegador:
echo http://127.0.0.1:4177
echo.

start "" "http://127.0.0.1:4177"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\serve-puter-home.ps1"

pause
