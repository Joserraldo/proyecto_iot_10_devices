@echo off
setlocal

REM Ejecuta el ESP32 de Wokwi y conserva todo el Serial Monitor en logs/.
set "REPO=%~dp0"
set "WOKWI_DIR=%REPO%wokwi"
set "LOG_DIR=%REPO%logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%I"
set "LOG_FILE=%LOG_DIR%\wokwi-d2-%STAMP%.log"

echo Iniciando Wokwi D2...
echo Log: %LOG_FILE%
echo Cierra la simulacion o presiona Ctrl+C para detenerla.
echo.

where wokwi-cli >nul 2>&1
if errorlevel 1 (
  echo ERROR: no se encontro wokwi-cli en PATH.
  echo Instala Wokwi CLI y vuelve a ejecutar este archivo.
  exit /b 1
)

cd /d "%WOKWI_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "& { wokwi-cli . --timeout 0 2^>^&1 | Tee-Object -FilePath '%LOG_FILE%' }"

echo.
echo Log guardado en: %LOG_FILE%
pause