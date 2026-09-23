#!/usr/bin/env bash
# start-device.sh — arranca UN componente de la flota Campus EMS.
#
# Uso:  start-device.sh <d1|d2|...|d10|dashboard>
#
# Lo usa el servicio systemd campus-ems@<nombre>.service, que ademas redirige
# stdout/stderr a ~/iotlogs/<nombre>.log (el dashboard lee esos archivos).
#
# Las credenciales NO viven aqui: se leen de /etc/campus-ems/fleet.env
# (chmod 600, fuera del repositorio). Ver ops/fleet.env.example
set -euo pipefail

NODE="${1:?uso: start-device.sh <d1..d10|dashboard>}"
REPO="${REPO_DIR:-$HOME/proyecto_iot_10_devices}"
PY="$REPO/venv/bin/python3"
ENV_FILE="${FLEET_ENV:-/etc/campus-ems/fleet.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
else
  echo "[start-device] AVISO: no existe $ENV_FILE — algunas variables faltaran" >&2
fi

mkdir -p "$HOME/iotlogs"
cd "$REPO/python"

case "$NODE" in
  d1) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D1:?falta CS_D1}" "$PY" sdk_node_d1.py ;;
  d2) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D2:?falta CS_D2}" \
            IOT_CENTRAL_DEVICE_ID_D2=campus-ems-02 "$PY" mqtt_bridge_wokwi.py ;;
  d3) exec env IOT_CENTRAL_DPS_CONNECTION="${CS_D3:?falta CS_D3}" \
            IOT_CENTRAL_DEVICE_ID=campus-ems-03 "$PY" sdk_node_d3.py ;;
  d4) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D4:?falta CS_D4}" "$PY" sdk_node_d4.py ;;
  d5) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D5:?falta CS_D5}" "$PY" api_node_d5.py ;;
  d6) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D6:?falta CS_D6}" "$PY" api_node_d6.py ;;
  d7) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D7:?falta CS_D7}" "$PY" sdk_node_d7.py ;;
  d8) exec env AZURE_CONNECTION_STRING="${CS_D8:?falta CS_D8}" \
            IOT_CENTRAL_DEVICE_ID_D8=campus-ems-08 D8_DEVICE_ID=campus-ems-08 \
            D8_INTERVAL="${D8_INTERVAL:-60}" "$PY" sdk_node_d8.py --send-to-cloud ;;
  d9) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D9:?falta CS_D9}" "$PY" sdk_node_d9.py ;;
  d10) exec env IOT_CENTRAL_DPS_CONNECTION_STRING="${CS_D10:?falta CS_D10}" "$PY" sdk_node_d10.py ;;
  dashboard) exec "$PY" dashboard_server.py ;;
  *) echo "[start-device] nodo desconocido: $NODE" >&2; exit 2 ;;
esac
