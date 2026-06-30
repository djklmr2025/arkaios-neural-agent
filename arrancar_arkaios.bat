@echo off
echo ========================================================
echo Iniciando Sistema ARKAIOS NeuralAgent (Entorno Local)
echo ========================================================
echo.

echo [1/3] Iniciando el Cerebro (Backend FastAPI)...
start "ARKAIOS - Backend" cmd /k "cd /d C:\ARKAIOS\neuralagentAI-main\backend && .\venv\Scripts\activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo [2/3] Iniciando el Cuerpo (Daemon Python - aiagent)...
start "ARKAIOS - Daemon" cmd /k "cd /d C:\ARKAIOS\neuralagentAI-main\desktop\aiagent && .\venv\Scripts\activate && python main.py"

echo [3/3] Iniciando la Interfaz Grafica (Frontend React + Electron)...
start "ARKAIOS - Interfaz UI" cmd /k "cd /d C:\ARKAIOS\neuralagentAI-main\desktop && npm start"

echo.
echo ========================================================
echo Las tres consolas se han abierto en ventanas separadas.
echo Por favor, espera a que la consola de "Interfaz UI" 
echo termine de compilar React y abra la aplicacion.
echo ========================================================
pause
