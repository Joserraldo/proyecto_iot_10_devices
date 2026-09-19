#!/usr/bin/env python3
"""
D7 - Acceso principal / Perímetro
-----------------------------------
Origen: MQTT Explícito (paho-mqtt publica en broker público)
        + reenvío opcional a Azure IoT Central via SDK.
Protocolo: MQTT (paho) para publicación; MQTT/TLS para IoT Central.
Intervalo: 30 segundos
Variables: door_status, occupancy, temperature, source, timestamp

NOTA: El dispositivo publica en un broker MQTT local/público (test.mqtt.org)
      y opcionalmente reenvía a IoT Central si IOT_CENTRAL_DPS_CONNECTION_STRING
      está configurada. Esto demuestra visibilidad explícita del protocolo MQTT.
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message

# MQTT explícito (broker público para demo; en producción usar broker privado)
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mosquitto.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_D7", "campus/ems/D7")

# Azure IoT Central (opcional — reenvío si hay credenciales)
CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D7", "campus-ems-07")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D7", "30"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D7] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    return {
        "door_status": random.random() > 0.6,    # 40 % abierta
        "occupancy": 1 if random.random() > 0.75 else 0,  # 25 % ocupado — int para Device Template (D9 usa 0/1/2)
        "temperature": round(random.uniform(15.0, 35.0), 1),
        "source": "mqtt-explicito",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# -------------------------------------------------------------------
# Callbacks MQTT
# -------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"[D7] Conectado a broker MQTT {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC + "/commands")
    else:
        logger.error(f"[D7] Fallo de conexión MQTT: código {rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"[D7] Desconexión inesperada MQTT: código {rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        command = payload.get("command", "")
        logger.info(f"[D7] Comando MQTT recibido en {msg.topic}: {command}")
    except Exception as e:
        logger.warning(f"[D7] Error procesando mensaje MQTT: {e}")


def connect_mqtt():
    client = mqtt.Client(client_id=f"d7-{DEVICE_ID}")
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
        return client
    except Exception as e:
        logger.error(f"[D7] Error conectando a broker MQTT: {e}")
        return None


def connect_azure():
    if not CONNECTION_STRING:
        logger.warning("[D7] IOT_CENTRAL_DPS_CONNECTION_STRING no configurada — solo MQTT local")
        return None
    try:
        azure = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        azure.connect()
        logger.info(f"[D7] {DEVICE_ID} también conectado a IoT Central")
        return azure
    except Exception as e:
        logger.warning(f"[D7] No se pudo conectar a IoT Central: {e}")
        return None


def main():
    logger.info("[D7] Iniciando — Acceso principal / Perímetro")
    logger.info(f"[D7] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s")
    logger.info(f"[D7] Broker MQTT: {MQTT_BROKER}:{MQTT_PORT} | Tópico: {MQTT_TOPIC}")

    mqtt_client = connect_mqtt()
    if mqtt_client is None:
        logger.error("[D7] No se pudo conectar al broker MQTT — saliendo")
        return

    azure_client = connect_azure()

    iteration = 0
    try:
        while True:
            iteration += 1
            telemetry = generate_telemetry()
            payload_str = json.dumps(telemetry)

            # 1. Publicar vía MQTT explícito
            result = mqtt_client.publish(MQTT_TOPIC, payload_str)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.warning(f"[D7] Error publicando MQTT: rc={result.rc}")

            # 2. Reenviar a IoT Central si está configurado
            if azure_client is not None:
                try:
                    msg = Message(payload_str)
                    msg.content_encoding = "utf-8"
                    msg.content_type = "application/json"
                    azure_client.send_message(msg)
                except Exception as e:
                    logger.error(f"[D7] Error reenviando a IoT Central: {e}")

            if iteration == 1 or iteration % 5 == 0:
                logger.info(
                    f"[D7] iter={iteration} puerta={telemetry['door_status']} "
                    f"ocupacion={telemetry['occupancy']} temp={telemetry['temperature']}°C"
                )
            else:
                logger.debug(f"[D7] iter={iteration} publicado en {MQTT_TOPIC}")

            time.sleep(SAMPLE_INTERVAL)

    except KeyboardInterrupt:
        logger.info("[D7] Detenido por usuario (Ctrl+C)")
    finally:
        try:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        except Exception as e:
            logger.warning(f"[D7] Error al cerrar MQTT: {e}")
        if azure_client is not None:
            try:
                azure_client.disconnect()
                logger.info("[D7] Desconectado de IoT Central")
            except Exception as e:
                logger.warning(f"[D7] Error al desconectar Azure: {e}")


if __name__ == "__main__":
    main()
