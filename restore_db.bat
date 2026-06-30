@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   ARKAIOS - Restaurar Backup de Supabase
echo ============================================

REM Buscar pg_restore en rutas comunes de PostgreSQL
set PG_BIN=
for %%v in (17 16 15 14) do (
    if exist "C:\Program Files\PostgreSQL\%%v\bin\psql.exe" (
        set PG_BIN=C:\Program Files\PostgreSQL\%%v\bin
        echo [OK] PostgreSQL %%v encontrado en !PG_BIN!
        goto :found
    )
)
echo [ERROR] PostgreSQL no encontrado. Instala primero.
pause
exit /b 1

:found
set PSQL="%PG_BIN%\psql.exe"
set PG_RESTORE="%PG_BIN%\pg_restore.exe"
set CREATEDB="%PG_BIN%\createdb.exe"

REM Configuracion de la DB local
set DB_USER=postgres
set DB_NAME=arkaios_db
set BACKUP_FILE=db_cluster-31-10-2025@05-54-33.backup.gz

echo.
echo [1/3] Creando base de datos '%DB_NAME%'...
%CREATEDB% -U %DB_USER% --encoding=UTF8 %DB_NAME% 2>nul
if errorlevel 1 echo [INFO] La DB ya existe o hubo un error menor, continuando...

echo.
echo [2/3] Restaurando backup (puede tardar 1-2 min)...
REM El backup es .gz - lo descomprimimos y restauramos
"%PG_BIN%\pg_restore.exe" -U %DB_USER% -d %DB_NAME% --no-owner --no-privileges --verbose "%~dp0%BACKUP_FILE%" 2>&1

echo.
echo [3/3] Verificando tablas restauradas...
%PSQL% -U %DB_USER% -d %DB_NAME% -c "\dt"

echo.
echo ============================================
echo   Backup restaurado. DB lista en:
echo   Host: localhost  Puerto: 5432
echo   DB: %DB_NAME%  User: %DB_USER%
echo ============================================
pause
