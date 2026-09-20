#!/usr/bin/env python3
"""
D4 - Incendio Laboratorio
--------------------------
Origen: Python SDK (azure-iot-device)
Protocolo: MQTT/TLS via DPS
Intervalo: 60 segundos
Variables: smoke, flame, temperature, co_level, door_status, timestamp
Extras: propiedades writable y comandos remotos (requieren callback en Fase 2)
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D4", "campus-ems-04")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D4", "60"))

FIRE_LOGIC = {
    "smoke_chance": 0.02,
    "flame_chance": 0.005,
    "temp_base": 22.0,
    "co_base": 25.0,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D4] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    smoke = random.random() < FIRE_LOGIC["smoke_chance"]
    flame = random.random() < FIRE_LOGIC["flame_chance"]
    temp = round(FIRE_LOGIC["temp_base"] + random.uniform(-3, 3), 1)
    co = round(FIRE_LOGIC["co_base"] + (10.0 if smoke else 0) + random.uniform(-5, 5), 1)
    return {
        "smoke": smoke,
        "flame": flame,
        "temperature": max(0.0, min(60.0, temp)),
        "co_level": max(0.0, min(200.0, co)),
        "door_status": smoke or flame,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# -------------------------------------------------------------------
# Comandos y propiedades writable — se activan en Fase 2 con Azure
# Para activar: client.on_method_request_received = handle_command
# -------------------------------------------------------------------
def handle_command(method_request):
    """
    Maneja comandos remotos (MethodRequest del SDK).
    NOTA: conectar en Fase 2 con client.on_method_request_received = handle_command
    """
    from azure.iot.device import MethodResponse
    name = method_request.name
    payload = method_request.payload or {}
    logger.info(f"[D4] Comando recibido: {name}")

    if name == "reboot_device":
        response_payload = {"status": "reboot_initiated", "device": DEVICE_ID}
        status = 200
    elif name == "test_sensors":
        sensor_list = payload.get("sensor_list", ["smoke", "flame", "temperature"])
        results = {}
        for s in sensor_list:
            if s == "smoke":
                results["smoke"] = random.random() < FIRE_LOGIC["smoke_chance"]
            elif s == "flame":
                results["flame"] = random.random() < FIRE_LOGIC["flame_chance"]
            elif s == "temperature":
                results["temperature"] = round(FIRE_LOGIC["temp_base"] + random.uniform(-3, 3), 1)
            elif s == "co_level":
                results["co_level"] = round(FIRE_LOGIC["co_base"] + random.uniform(-5, 5), 1)
        response_payload = {"sensor_results": results}
        status = 200
    else:
        logger.warning(f"[D4] Comando desconocido: {name}")
        response_payload = {"error": "unknown_command"}
        status = 400

    return MethodResponse.create_from_method_request(method_request, status, response_payload)


def connect_client():
    if not CONNECTION_STRING:
        logger.error("[D4] IOT_CENTRAL_DPS_CONNECTION_STRING no configurada")
        return None
    try:
        client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        client.connect()
        logger.info(f"[D4] {DEVICE_ID} conectado a IoT Central")
        return client
    except Exception as e:
        logger.error(f"[D4] Error al conectar: {e}")
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
                if iteration == 1 or iteration % 5 == 0 or smoke_val or flame_val:
                    logger.info(
                        f"[D4] iter={iteration} temp={telemetry['temperature']}°C "
                        f"CO={telemetry['co_level']}ppm smoke={smoke_val} flame={flame_val}"
                    )
                else:
                    logger.debug(f"[D4] iter={iteration} telemetría enviada")
            except Exception as e:
                logger.error(f"[D4] Error enviando telemetría iter={iteration}: {e}")
                time.sleep(5)
                continue
            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D4] Detenido por usuario (Ctrl+C)")
    finally:
        try:
            client.disconnect()
            logger.info("[D4] Desconectado")
        except Exception as e:
            logger.warning(f"[D4] Error al desconectar: {e}")


def main():
    logger.info("[D4] Iniciando — Incendio Laboratorio")
    logger.info(f"[D4] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s")
    client = connect_client()
    if client is None:
        logger.error("[D4] No se pudo conectar — saliendo")
        return
    # Fase 2: habilitar comandos con:
    # client.on_method_request_received = lambda req: client.send_method_response(handle_command(req))
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()
