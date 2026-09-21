#!/usr/bin/env python3
"""
D10 - Puesto de mando
----------------------
Origen: Python SDK (IoTHubDeviceClient via DPS)
Protocolo: MQTT/TLS
Intervalo: 20 segundos (el más frecuente de la flota)
Variables (aplanadas para IoT Central):
  connected_devices, disconnected_devices, system_health,
  temperatura_promedio, ack_pending, ack_status, system_uptime,
  mqtt_status, timestamp

NOTA: El JSON anidado original (estado_agregado, confirmacion_ack)
      fue aplanado porque IoT Central procesa telemetría plana.
      Los campos compuestos requieren Components en el Device Template (Fase 2).
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D10", "campus-ems-10")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D10", "20"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D10] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    connected = random.randint(8, 10)
    disconnected = 10 - connected
    ack_options = [
        (0, "all_clear"),
        (1, "active_alert"),
        (2, "minor_issues"),
    ]
    ack_pending, ack_status = random.choice(ack_options)
    return {
        # Estado de flota — aplanado
        "connected_devices": connected,
        "disconnected_devices": disconnected,
        "system_health": round(random.uniform(85.0, 100.0), 1),
        # Temperatura promedio ponderada
        "temperatura_promedio": round(random.uniform(18.0, 28.0), 1),
        # ACK de alarmas — aplanado
        "ack_pending": ack_pending,
        "ack_status": ack_status,
        # Métricas de sistema
        "system_uptime": round(random.uniform(95.0, 100.0), 1),
        "mqtt_status": random.choices(
            ["connected", "reconnecting"], weights=[0.95, 0.05], k=1
        )[0],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def connect_client():
    if not CONNECTION_STRING:
        logger.error("[D10] IOT_CENTRAL_DPS_CONNECTION_STRING no configurada")
        return None
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
        logger.info(f"[D10] {DEVICE_ID} conectado a IoT Central")
        return client
    except Exception as e:
        logger.error(f"[D10] Error al conectar: {e}")
        return None


def send_periodic_telemetry(client):
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
                logger.info(f"[D10] TELE {json.dumps(telemetry)}")
                if iteration == 1 or iteration % 10 == 0:
                    logger.info(
                        f"[D10] iter={iteration} "
                        f"connected={telemetry['connected_devices']}/10 "
                        f"ack={telemetry['ack_status']} "
                        f"temp_prom={telemetry['temperatura_promedio']}°C"
                    )
                else:
                    logger.debug(f"[D10] iter={iteration} telemetría enviada")
            except Exception as e:
                logger.error(f"[D10] Error enviando iter={iteration}: {e}")
                time.sleep(5)
                continue
            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D10] Detenido por usuario (Ctrl+C)")
    finally:
        try:
            client.disconnect()
            logger.info("[D10] Desconectado")
        except Exception as e:
            logger.warning(f"[D10] Error al desconectar: {e}")


def main():
    logger.info("[D10] Iniciando — Puesto de mando")
    logger.info(f"[D10] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s (el más frecuente)")
    client = connect_client()
    if client is None:
        logger.error("[D10] No se pudo conectar — saliendo")
        return
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()
