@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo  NeuralAgent DEV - ejecutable instalado
echo ==========================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-installed-dev.ps1" -RestartApp

echo.
echo Si no hubo errores, NeuralAgent ya esta abierto.
echo Backend: http://127.0.0.1:8000
echo Bridge token: %%LOCALAPPDATA%%\NeuralAgent\local_bridge_token.txt
echo.
pause
