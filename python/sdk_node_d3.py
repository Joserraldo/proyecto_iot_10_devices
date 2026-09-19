#!/usr/bin/env python3
"""
D3 - Incendio Bloque A
-----------------------
Origen: Python SDK (azure-iot-device)
Protocolo: MQTT/TLS via DPS
Intervalo: 60 segundos
Variables: temperature, smoke, flame, co_level, timestamp
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID", "campus-ems-03")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D3", "60"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D3] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    smoke = random.random() < 0.02      # 2 % de probabilidad
    flame = random.random() < 0.005     # 0.5 % de probabilidad
    return {
        "temperature": round(22.0 + random.uniform(-3, 3) + (8.0 if smoke else 0), 1),
        "smoke": smoke,
        "flame": flame,
        "co_level": round(25.0 + (10.0 if smoke else 0) + random.uniform(-5, 5), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def connect_client():
    if not CONNECTION_STRING:
        logger.error("[D3] IOT_CENTRAL_DPS_CONNECTION no configurada")
        return None
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
        logger.info(f"[D3] {DEVICE_ID} conectado a IoT Central")
        return client
    except Exception as e:
        logger.error(f"[D3] Error al conectar: {e}")
        return None


def send_periodic_telemetry(client):
    """Loop principal: genera y envía telemetría cada SAMPLE_INTERVAL segundos."""
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
                smoke_val = telemetry["smoke"]
                flame_val = telemetry["flame"]
                temp = telemetry["temperature"]
                co = telemetry["co_level"]
                if iteration == 1 or iteration % 5 == 0 or smoke_val or flame_val:
                    logger.info(
                        f"[D3] iter={iteration} temp={temp}°C CO={co}ppm "
                        f"smoke={smoke_val} flame={flame_val}"
                    )
                else:
                    logger.debug(f"[D3] iter={iteration} telemetría enviada")
            except Exception as e:
                logger.error(f"[D3] Error enviando telemetría iter={iteration}: {e}")
                time.sleep(5)
                continue
            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D3] Detenido por usuario (Ctrl+C)")
    finally:
        try:
            client.disconnect()
            logger.info("[D3] Desconectado")
        except Exception as e:
            logger.warning(f"[D3] Error al desconectar: {e}")


def main():
    logger.info("[D3] Iniciando — Incendio Bloque A")
    logger.info(f"[D3] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s")
    client = connect_client()
    if client is None:
        logger.error("[D3] No se pudo conectar — saliendo")
        return
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()
