#!/usr/bin/env python3
"""
D8 - Cerramiento norte (Replay CSV + Desconexión controlada)
-------------------------------------------------------------
Origen: Replay CSV histórico
Protocolo: Local (sin red) o MQTT/TLS hacia IoT Central con --send-to-cloud
Intervalo: 60 segundos
Variables: motion, lux_nocturno, temperature (desde perimetro_norte_4dias.csv)

Desconexión controlada:
  --disconnect-at N   pausa el envío en la iteración N durante 2×INTERVALO
  y luego reanuda. Sirve para demostrar el requisito de desconexión documentada.

Uso:
  python sdk_node_d8.py                           # replay local (sin Azure)
  python sdk_node_d8.py --disconnect-at 5         # desconexión en iter 5
  python sdk_node_d8.py --send-to-cloud           # envío real a Azure
  python sdk_node_d8.py --send-to-cloud --disconnect-at 5 --iterations 10
"""

import os
import json
import time
import csv
import argparse
import random
import logging
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D8] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("D8")

INTERVAL = float(os.getenv("D8_INTERVAL", "60"))
DEVICE_ID = os.getenv("D8_DEVICE_ID", "campus-ems-08")
CSV_PATH = os.getenv(
    "D8_CSV_PATH",
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "perimetro_norte_4dias.csv",
    ),
)


def load_csv_rows(path):
    """Carga filas del CSV histórico; genera mock si el archivo falta."""
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get("timestamp", "").strip()
                if ts and not ts.startswith("<!--") and ts != "...":
                    rows.append(row)
        if rows:
            logger.info(f"[D8] CSV cargado: {len(rows)} filas desde {path}")
        else:
            logger.warning(f"[D8] CSV vacío o sin filas válidas — usando datos mock")
            rows = generate_mock_csv_data()
    except FileNotFoundError:
        logger.warning(f"[D8] CSV no encontrado en {path} — usando datos mock")
        rows = generate_mock_csv_data()
    except Exception as e:
        logger.error(f"[D8] Error cargando CSV: {e} — usando datos mock")
        rows = generate_mock_csv_data()
    return rows


def generate_mock_csv_data():
    """Genera datos mock para pruebas locales cuando el CSV no está disponible."""
    base = datetime.now(timezone.utc) - timedelta(hours=96)  # 4 días atrás
    rows = []
    for i in range(240):  # 240 filas × 60 min = aprox 4 días
        ts = base + timedelta(hours=i)
        rows.append({
            "timestamp": ts.isoformat(),
            "motion": "1" if random.random() > 0.7 else "0",
            "lux_nocturno": str(round(random.uniform(30, 45), 1)),
            "temperature": str(round(random.uniform(18, 22), 1)),
        })
    logger.info(f"[D8] Mock generado: {len(rows)} filas")
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
    disconnect_iter = disconnect_at if disconnect_at else float("inf")

    client = None
    if send_to_cloud:
        conn_str = os.getenv("AZURE_CONNECTION_STRING") or os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
        if conn_str:
            try:
                from azure.iot.device import IoTHubDeviceClient
                client = IoTHubDeviceClient.create_from_connection_string(conn_str)
                client.connect()
                logger.info(f"[D8] {DEVICE_ID} conectado a IoT Central")
            except Exception as e:
                logger.error(f"[D8] No se pudo conectar a IoT Central: {e}")
                client = None
        else:
            logger.error("[D8] --send-to-cloud requiere AZURE_CONNECTION_STRING o IOT_CENTRAL_DPS_CONNECTION_STRING")

    disconnect_timestamp = None
    reconnect_timestamp = None
    i = 0

    try:
        while iterations is None or i < iterations:
            i += 1
            row = rows[(i - 1) % len(rows)]

            if i == disconnect_iter:
                logger.warning(f"[D8] iter={i} >>> DESCONEXIÓN CONTROLADA: deteniendo envío")
                disconnect_timestamp = datetime.now(timezone.utc).isoformat()
                logger.info(f"[D8] T_desconexión: {disconnect_timestamp}")
                time.sleep(INTERVAL * 2)      # hueco de 2 intervalos
                reconnect_timestamp = datetime.now(timezone.utc).isoformat()
                logger.info(f"[D8] T_reconexión: {reconnect_timestamp}")
                logger.info(f"[D8] iter={i} >>> RECONEXIÓN: reanudando envío (~{INTERVAL * 2:.0f}s de hueco)")
                continue

            payload = generate_payload(row, i)

            if client is not None:
                try:
                    from azure.iot.device import Message
                    msg = Message(json.dumps(payload))
                    msg.content_encoding = "utf-8"
                    msg.content_type = "application/json"
                    client.send_message(msg)
                    logger.info(
                        f"[D8] iter={i} → Central: motion={payload['motion']} "
                        f"lux={payload['lux_nocturno']} temp={payload['temperature']}°C"
                    )
                except Exception as e:
                    logger.error(f"[D8] Error enviando iter={i}: {e}")
            else:
                print(json.dumps(payload, ensure_ascii=False))
                logger.info(
                    f"[D8] iter={i} (local): motion={payload['motion']} "
                    f"lux={payload['lux_nocturno']} temp={payload['temperature']}°C"
                )

            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        logger.info("[D8] Detenido por usuario (Ctrl+C)")
    finally:
        if client is not None:
            try:
                client.disconnect()
                logger.info("[D8] Desconectado de IoT Central")
            except Exception as e:
                logger.warning(f"[D8] Error al desconectar: {e}")

    if disconnect_timestamp and reconnect_timestamp:
        logger.info("=== EVIDENCIA DESCONEXIÓN CONTROLADA ===")
        logger.info(f"T desconexión : {disconnect_timestamp}")
        logger.info(f"T reconexión  : {reconnect_timestamp}")
        logger.info(f"Hueco de datos: ~{INTERVAL * 2:.0f}s (2 intervalos sin telemetría)")


def main():
    parser = argparse.ArgumentParser(
        description="D8 Cerramiento norte — Replay CSV con desconexión controlada"
    )
    parser.add_argument("--disconnect-at", type=int, default=None,
                        help="Iteración donde simular desconexión controlada")
    parser.add_argument("--send-to-cloud", action="store_true",
                        help="Enviar a Azure IoT Central (requiere variable de entorno con connection string)")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Número máximo de iteraciones (para pruebas rápidas)")
    args = parser.parse_args()
    run(args.disconnect_at, args.send_to_cloud, args.iterations)


if __name__ == "__main__":
    main()
