#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WOKWI_DIR="$REPO_DIR/wokwi"
LOG_DIR="$REPO_DIR/logs"
mkdir -p "$LOG_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/wokwi-d2-$STAMP.log"

if ! command -v wokwi-cli >/dev/null 2>&1; then
  echo "ERROR: no se encontro wokwi-cli en PATH."
  echo "Instala Wokwi CLI y vuelve a ejecutar este script."
  exit 1
fi

echo "Iniciando Wokwi D2 en esta terminal..."
echo "Log: $LOG_FILE"
echo "Presiona Ctrl+C para detenerlo."
echo

cd "$WOKWI_DIR"
wokwi-cli . --timeout 0 2>&1 | tee "$LOG_FILE"