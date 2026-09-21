#!/usr/bin/env python3
"""
D1 - Estación meteo campus
--------------------------
Origen: Python SDK (IoTHubDeviceClient via DPS)
Protocolo: MQTT/TLS
Intervalo: 15 segundos
Variables: temperature, humidity, pressure, wind_speed, wind_direction, rainfall
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

# Credenciales desde variables de entorno — NUNCA hardcodeadas
CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D1", "campus-ems-01")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D1", "15"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D1] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    temp = round(25.0 + random.uniform(-5, 5), 1)
    hum = round(max(20.0, min(80.0, 60.0 - (temp - 20) * 0.3 + random.uniform(-10, 10))), 1)
    return {
        "temperature": temp,
        "humidity": hum,
        "pressure": round(1013.25 + random.uniform(-5, 5), 1),
        "wind_speed": round(max(0.0, min(50.0, 5.0 + random.uniform(-3, 3))), 1),
        "wind_direction": round(random.uniform(0, 360), 1),
        "rainfall": round(random.uniform(0, 5), 1) if random.random() > 0.7 else 0.0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def connect_client():
    if not CONNECTION_STRING:
        logger.error("[D1] IOT_CENTRAL_DPS_CONNECTION_STRING no configurada")
        return None
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
        logger.info(f"[D1] {DEVICE_ID} conectado a IoT Central")
        return client
    except Exception as e:
        logger.error(f"[D1] Error al conectar: {e}")
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
                logger.info(f"[D1] TELE {json.dumps(telemetry)}")
                if iteration == 1 or iteration % 10 == 0:
                    logger.info(
                        f"[D1] iter={iteration} temp={telemetry['temperature']}°C "
                        f"hum={telemetry['humidity']}% viento={telemetry['wind_speed']}m/s"
                    )
                else:
                    logger.debug(f"[D1] iter={iteration} telemetría enviada")
            except Exception as e:
                logger.error(f"[D1] Error enviando telemetría iter={iteration}: {e}")
                time.sleep(5)
                continue
            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D1] Detenido por usuario (Ctrl+C)")
    finally:
        try:
            client.disconnect()
            logger.info("[D1] Desconectado")
        except Exception as e:
            logger.warning(f"[D1] Error al desconectar: {e}")


def main():
    logger.info("[D1] Iniciando — Estación meteo campus")
    logger.info(f"[D1] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s")
    client = connect_client()
    if client is None:
        logger.error("[D1] No se pudo conectar — saliendo")
        return
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()
