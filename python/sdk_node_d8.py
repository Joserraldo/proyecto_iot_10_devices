#!/usr/bin/env python3
"""
D8 - Cerramiento norte (Replay CSV + DESCONEXION CONTROLADA)
Variables: motion, lux nocturno, temperature. Intervalo 60s. Asincronia #6.
Replay: lee data/perimetro_norte_4dias.csv (datos de 4 dias no consecutivos).
Desconexion controlada: con flag --disconnect-at N detiene envio N iteraciones y reconecta.
Uso:
  python sdk_node_d8.py                        # modo replay normal
  python sdk_node_d8.py --disconnect-at 5      # desconexion en iteracion 5

Modo evidencia (sin Azure): el script imprime timestamps por cada envio.
"""

import os
import json
import time
import csv
import argparse
import random
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [D8] %(levelname)s - %(message)s")
logger = logging.getLogger("D8")

INTERVAL = float(os.getenv("D8_INTERVAL", "60"))
DEVICE_ID = os.getenv("D8_DEVICE_ID", "d8-cerramiento-norte")
CSV_PATH = os.getenv(
    "D8_CSV_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "perimetro_norte_4dias.csv"),
)


def load_csv_rows(path):
    """Carga datos desde el archivo CSV historico; genera mock si falta."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("timestamp", "").strip() and not row["timestamp"].startswith("<!--"):
                    rows.append(row)
        logger.info(f"CSV cargado: {len(rows)} filas desde {path}")
    except FileNotFoundError:
        logger.warning(f"CSV {path} no encontrado; generando datos mock")
        return generate_mock_csv_data()
    except Exception as e:
        logger.error(f"Cargando CSV no se pudo: {e}")
        return generate_mock_csv_data()
    return rows


def generate_mock_csv_data():
    """Genera datos mock CSV si el archivo no está disponible."""
    base = datetime.now(timezone.utc) - timedelta(hours=24 * 4)
    rows = []
    for i in range(60):
        rows.append({
            "timestamp": (base + datetime.timedelta(minutes=i * 60)).isoformat(),
            "motion": "1" if random.random() > 0.7 else "0",
            "lux_nocturno": str(round(random.uniform(30, 45), 1)),
            "temperature": str(round(random.uniform(18, 22), 1)),
        })
    return rows


def generate_payload(row, idx):
    return {
        "motion": row["motion"] == "1",
        "lux_nocturno": round(float(row["lux_nocturno"]), 1),
        "temperature": round(float(row["temperature"]), 1),
        "source": "csv-replay",
        "csv_row": idx,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_id": DEVICE_ID,
    }


def run(disconnect_at=None, send_to_cloud=False, iterations=None):
    rows = load_csv_rows(CSV_PATH)
    if not disconnect_at:
        disconnect_at = float("inf")

    client = None
    if send_to_cloud and os.getenv("AZURE_CONNECTION_STRING"):
        from azure.iot.device import IoTHubDeviceClient
        client = IoTHubDeviceClient.create_from_connection_string(os.getenv("AZURE_CONNECTION_STRING"))
        client.connect()

    i = 0
    disconnect_timestamp = None
    reconnect_timestamp = None
    try:
        while iterations is None or i < iterations:
            i += 1
            row = rows[(i - 1) % len(rows)]

            if i == disconnect_at:
                logger.warning(f"[{i}] >>> DESCONEXION CONTROLADA: deteniendo envio")
                disconnect_timestamp = datetime.now(timezone.utc).isoformat()
                logger.info(f"DESCONEXION timestamp: {disconnect_timestamp}")
                time.sleep(INTERVAL * 2)
                reconnect_timestamp = datetime.now(timezone.utc).isoformat()
                logger.info(f"RECONEXION timestamp: {reconnect_timestamp}")
                logger.info(f"[{i}] >>> RECONEXION: reanudando envio (hueco ~{INTERVAL * 2}s)")
                continue

            payload = generate_payload(row, i)
            if client:
                client.send_message(json.dumps(payload))
                logger.info(f"[{i}] Enviado a Central: motion={payload['motion']} lux={payload['lux_nocturno']}")
            else:
                print(json.dumps(payload, ensure_ascii=False))
                logger.info(
                    f"[{i}] Enviado: motion={payload['motion']} lux={payload['lux_nocturno']} "
                    f"temp={payload['temperature']}"
                )

            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        logger.info("Detenido por usuario")
    finally:
        if client:
            client.disconnect()

    if disconnect_timestamp and reconnect_timestamp:
        logger.info("=== EVIDENCIA DESCONEXION CONTROLADA ===")
        logger.info(f"T desconexion : {disconnect_timestamp}")
        logger.info(f"T reconexion  : {reconnect_timestamp}")
        logger.info(f"Hueco de datos: ~{INTERVAL * 2}s (sin telemetria entre ambos)")


def main():
    parser = argparse.ArgumentParser(description="D8 Cerramiento norte - Replay CSV con desconexion controlada")
    parser.add_argument("--disconnect-at", type=int, default=None,
                        help="Iteracion donde simular desconexion controlada")
    parser.add_argument("--send-to-cloud", action="store_true",
                        help="Enviar a Azure IoT Central (requiere AZURE_CONNECTION_STRING)")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Maximo de iteraciones (para pruebas rapidas)")
    args = parser.parse_args()
    run(args.disconnect_at, args.send_to_cloud, args.iterations)


if __name__ == "__main__":
    main()