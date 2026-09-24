@echo off
REM ============================================================
REM run_all_devices.bat — Lanza los 9 dispositivos Python en
REM ventanas separadas. Cada ventana mantiene el dispositivo
REM conectado a Azure IoT Central de forma continua.
REM
REM USO:
REM   1) Copiar devices.env.example a devices.env y pegar los
REM      connection strings de TU app de IoT Central (DPS).
REM   2) Doble clic en este archivo desde el repo.
REM Para detener: cerrar cada ventana o Ctrl+C en cada una.
REM ============================================================

set REPO=%~dp0
set PY=%REPO%python

REM Cargar credenciales desde devices.env (NO versionado)
if not exist "%REPO%devices.env" (
  echo [ERROR] No existe devices.env. Copia devices.env.example y completa tus credenciales.
  exit /b 1
)
for /f "usebackq delims=" %%a in ("%REPO%devices.env") do set "%%a"

if not defined CS_D1 (
  echo [ERROR] devices.env no tiene CS_D1..CS_D10. Revisa el archivo.
  exit /b 1
)

echo Iniciando flota campus-ems...

start "D1 - Estacion meteo"   cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D1% && cd /d "%PY%" && py sdk_node_d1.py"
timeout /t 2 /nobreak >nul

start "D3 - Incendio Bloque A" cmd /k "set IOT_CENTRAL_DPS_CONNECTION=%CS_D3% && set IOT_CENTRAL_DEVICE_ID=campus-ems-03 && cd /d "%PY%" && py sdk_node_d3.py"
timeout /t 2 /nobreak >nul

start "D4 - Incendio Lab"      cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D4% && cd /d "%PY%" && py sdk_node_d4.py"
timeout /t 2 /nobreak >nul

start "D5 - Calidad aula"      cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D5% && cd /d "%PY%" && py api_node_d5.py"
timeout /t 2 /nobreak >nul

start "D6 - Calidad exterior"  cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D6% && cd /d "%PY%" && py api_node_d6.py"
timeout /t 2 /nobreak >nul

start "D7 - Acceso principal"  cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D7% && cd /d "%PY%" && py sdk_node_d7.py"
timeout /t 2 /nobreak >nul

start "D8 - Cerramiento norte" cmd /k "set AZURE_CONNECTION_STRING=%CS_D8% && set D8_INTERVAL=60 && cd /d "%PY%" && py sdk_node_d8.py --send-to-cloud"
timeout /t 2 /nobreak >nul

start "D9 - Evacuacion pasillo" cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D9% && cd /d "%PY%" && py sdk_node_d9.py"
timeout /t 2 /nobreak >nul

start "D10 - Puesto de mando"  cmd /k "set IOT_CENTRAL_DPS_CONNECTION_STRING=%CS_D10% && cd /d "%PY%" && py sdk_node_d10.py"

echo.
echo 9 dispositivos iniciados en ventanas separadas.
echo Para detener todo: cierra cada ventana CMD.