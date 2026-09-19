#!/usr/bin/env python3
"""
D9 - Evacuación pasillo
------------------------
Origen: Python SDK (IoTHubDeviceClient via DPS)
Protocolo: MQTT/TLS
Intervalo: 45 segundos
Variables: occupancy, lux_emergency, temperature, emergency_status, timestamp
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D9", "campus-ems-09")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D9", "45"))
EMERGENCY_LUX_THRESHOLD = float(os.getenv("EMERGENCY_LUX_THRESHOLD", "20.0"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D9] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    # occupancy: 0=vacío, 1=ocupado, 2=densidad alta
    occupancy = random.choices([0, 1, 2], weights=[0.70, 0.25, 0.05], k=1)[0]
    lux = round(random.uniform(0, 200), 1)
    emergency = "active" if random.random() > 0.95 else "normal"
    if emergency == "active":
        lux = round(random.uniform(0, EMERGENCY_LUX_THRESHOLD), 1)
    return {
        "occupancy": occupancy,
        "lux_emergency": lux,
        "temperature": round(random.uniform(18.0, 28.0), 1),
        "emergency_status": emergency,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def connect_client():
    if not CONNECTION_STRING:
        logger.error("[D9] IOT_CENTRAL_DPS_CONNECTION_STRING no configurada")
        return None
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
        logger.info(f"[D9] {DEVICE_ID} conectado a IoT Central")
        return client
    except Exception as e:
        logger.error(f"[D9] Error al conectar: {e}")
        return None


def send_periodic_telemetry(client):
    """Loop principal con manejo correcto de try/except/finally."""
    iteration = 0
    try:
        while True:
            iteration += 1
            try:
                telemetry = generate_telemetry()
                msg = Message(json.dumps(telemetry))
                msg.content_encoding = "utf-8"
                msg.content_type = "application/json"
                client.send_message(msg)
                if iteration == 1 or iteration % 10 == 0 or telemetry["emergency_status"] == "active":
                    logger.info(
                        f"[D9] iter={iteration} occ={telemetry['occupancy']} "
                        f"lux={telemetry['lux_emergency']}lux emergency={telemetry['emergency_status']}"
                    )
                else:
                    logger.debug(f"[D9] iter={iteration} telemetría enviada")
            except Exception as e:
                logger.error(f"[D9] Error enviando iter={iteration}: {e}")
                time.sleep(5)
                continue
            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D9] Detenido por usuario (Ctrl+C)")
    finally:
        try:
            client.disconnect()
            logger.info("[D9] Desconectado")
        except Exception as e:
            logger.warning(f"[D9] Error al desconectar: {e}")


def main():
    logger.info("[D9] Iniciando — Evacuación pasillo")
    logger.info(f"[D9] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s")
    client = connect_client()
    if client is None:
        logger.error("[D9] No se pudo conectar — saliendo")
        return
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()
