@echo off
REM ============================================================
REM run_dashboard_local.bat - Lanza el panel Campus EMS localmente
REM (sin depender de la VM). Abre el navegador en el panel.
REM
REM USO: doble clic desde la raiz del repo. Detener: cerrar la ventana.
REM ============================================================
set "ROOT=%~dp0"
set "PY=%ROOT%python"
cd /d "%PY%"

echo [CampusEMS] Arrancando dashboard en http://127.0.0.1:8080 ...
echo [CampusEMS] Presiona Ctrl+C para detener.

start "" http://127.0.0.1:8080/
python dashboard_server.py --port 8080
