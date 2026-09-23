#!/usr/bin/env bash
# install-systemd.sh — instala la flota Campus EMS como servicios systemd.
#
# Deja los 10 nodos + dashboard arrancando automaticamente en cada boot y
# reiniciandose solos si un nodo se cae (Restart=always).
#
# Uso (en la VM):
#   sudo bash ops/install-systemd.sh
#
# Requiere que exista /etc/campus-ems/fleet.env (ver ops/fleet.env.example).
set -euo pipefail

REPO="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
NODES="d1 d2 d3 d4 d5 d6 d7 d8 d9 d10 dashboard"
ENV_FILE="/etc/campus-ems/fleet.env"
TARGET_USER="${TARGET_USER:-azureuser}"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: falta $ENV_FILE. Crear con ops/fleet.env.example antes de continuar." >&2
  exit 1
fi
chmod 600 "$ENV_FILE"
chown "$TARGET_USER:$TARGET_USER" "$ENV_FILE"

chmod 755 "$REPO/ops/start-device.sh"
install -m 644 "$REPO/ops/campus-ems@.service" /etc/systemd/system/campus-ems@.service
mkdir -p "/home/$TARGET_USER/iotlogs"
chown "$TARGET_USER:$TARGET_USER" "/home/$TARGET_USER/iotlogs"

systemctl daemon-reload
for n in $NODES; do
  systemctl enable --now "campus-ems@$n.service"
  echo "habilitado campus-ems@$n"
done

systemctl --no-pager --no-legend list-units 'campus-ems@*' || true
