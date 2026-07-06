@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==========================================
echo  NeuralAgent Completo DEV
echo ==========================================
echo.
echo 1/3 Arrancando backend y ejecutable instalado...

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-installed-dev.ps1" -RestartApp
if errorlevel 1 (
    echo.
    echo ERROR: No se pudo arrancar NeuralAgent DEV.
    pause
    exit /b 1
)

echo.
echo 2/3 Esperando servicios locales...
timeout /t 3 /nobreak >nul

echo.
echo 3/3 Arrancando Puter OS (Local)...
start "NeuralAgent Puter OS" powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\start-puter-os.ps1" -Restart

timeout /t 3 /nobreak >nul

echo.
echo ==========================================
echo  Listo
echo ==========================================
echo.
echo NeuralAgent instalado: abierto
echo Backend local: http://127.0.0.1:8000
echo Puter Home: http://127.0.0.1:4177
echo Bridge token:
echo   %%LOCALAPPDATA%%\NeuralAgent\local_bridge_token.txt
echo.
echo Puedes cerrar esta ventana cuando quieras. El servidor de Puter Home quedo en otra ventana.
echo.
pause
