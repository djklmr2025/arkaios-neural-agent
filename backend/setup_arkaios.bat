@echo off
echo ============================================
echo   ARKAIOS Backend Setup
echo ============================================

set PYTHON=C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312\python.exe

if not exist "%PYTHON%" (
    set PYTHON=C:\Program Files\Python312\python.exe
)

echo [1/4] Creando entorno virtual...
"%PYTHON%" -m venv venv

echo [2/4] Activando venv...
call venv\Scripts\activate.bat

echo [3/4] Instalando dependencias...
pip install -r requirements.txt

echo [4/4] Verificando importaciones clave...
python -c "import fastapi; import langchain_google_genai; print('OK - Todo listo!')"

echo.
echo ============================================
echo   Backend listo. Para iniciar:
echo   venv\Scripts\activate
echo   uvicorn main:app --reload --host 0.0.0.0 --port 8000
echo ============================================
pause
