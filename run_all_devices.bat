@echo off
REM ============================================================
REM run_all_devices.bat — Lanza los 9 dispositivos Python en
REM ventanas separadas. Cada ventana mantiene el dispositivo
REM conectado a Azure IoT Central de forma continua.
REM
REM USO: doble clic en este archivo desde el repo
REM Para detener: cerrar cada ventana o Ctrl+C en cada una
REM ============================================================

set REPO=C:\Users\buitr\OneDrive\trabajos\Nueva carpeta\proyecto_iot_10_devices
set PY=%REPO%\python

set HUB=iotc-ae3518fb-6e3f-48c4-b0c4-d6886902134d.azure-devices.net

set CS_D1=HostName=%HUB%;DeviceId=campus-ems-01;SharedAccessKey=P4JKcFZTDIbJsnCoM0EeWXIDCPHQXYarzNRl3HNHF8c=
set CS_D3=HostName=%HUB%;DeviceId=campus-ems-03;SharedAccessKey=lOBodmNRKAtsaiHUisLEHz7M0tEY9Wt+wWEsK1MZKeE=
set CS_D4=HostName=%HUB%;DeviceId=campus-ems-04;SharedAccessKey=Tfv/4mKXnxBs+P2Btm50QdAd0smxqgk3KgpNFG38muA=
set CS_D5=HostName=%HUB%;DeviceId=campus-ems-05;SharedAccessKey=5lcslo6iqnP6X7x9+sapp4/8mKu3/SnWKZwF9xUAzKY=
set CS_D6=HostName=%HUB%;DeviceId=campus-ems-06;SharedAccessKey=71JgPW2JaNB4iZ1OqCh9Top7wA9/l1JdEI/wXw7Kqos=
set CS_D7=HostName=%HUB%;DeviceId=campus-ems-07;SharedAccessKey=iJnTW8/0Fi7FKbN/Gf1t1KQz/Q+siYQ8plFXDCIab68=
set CS_D8=HostName=%HUB%;DeviceId=campus-ems-08;SharedAccessKey=cXiloZwxpstPN1U58AFpZJWOMnzLMmJg2Cc6EcE+Wqs=
set CS_D9=HostName=%HUB%;DeviceId=campus-ems-09;SharedAccessKey=YYFdBobnKSI7/82WpTVEYyhIzVBXQww1bazap0OiVh0=
set CS_D10=HostName=%HUB%;DeviceId=campus-ems-10;SharedAccessKey=JTAVBdPIhtCUXUun2M7CnOpT7UO6LZ2JuD5ltRvaoXo=

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
