#!/usr/bin/env python3
"""
Bridge MQTT — Wokwi → Azure IoT Central (D2)
----------------------------------------------
Escucha mensajes MQTT publicados por el simulador Wokwi (ESP32 D2)
y los reenvía a Azure IoT Central.

Flujo:
  Wokwi ESP32 → publica en MQTT_BROKER/WOKWI_TOPIC
    → este bridge suscribe y lee el mensaje
    → agrega metadatos de origen
    → reenvía a IoT Central via SDK

Requisitos:
  - Wokwi debe estar publicando en el tópico configurado
  - IOT_CENTRAL_DPS_CONNECTION_STRING en .env para el reenvío

Uso:
  python mqtt_bridge_wokwi.py
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message

# Broker donde publica el simulador Wokwi
WOKWI_BROKER = os.getenv("WOKWI_MQTT_BROKER", "test.mosquitto.org")
WOKWI_PORT = int(os.getenv("WOKWI_MQTT_PORT", "1883"))
WOKWI_TOPIC = os.getenv("WOKWI_MQTT_TOPIC", "campus/ems/D2")

# Azure IoT Central
CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D2", "campus-ems-02")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRIDGE-D2] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Cliente Azure persistente (se crea una vez, no por mensaje)
_azure_client = None


def get_azure_client():
    global _azure_client
    if _azure_client is not None:
        return _azure_client
    if not CONNECTION_STRING:
        logger.warning("[BRIDGE-D2] IOT_CENTRAL_DPS_CONNECTION_STRING no configurada — solo consola")
        return None
    try:
        _azure_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        _azure_client.connect()
        logger.info(f"[BRIDGE-D2] {DEVICE_ID} conectado a IoT Central")
    except Exception as e:
        logger.error(f"[BRIDGE-D2] Error al conectar a IoT Central: {e}")
        _azure_client = None
    return _azure_client


def forward_to_azure(payload: dict):
    """Reenvía el payload de Wokwi a Azure IoT Central."""
    global _azure_client
    client = get_azure_client()
    if client is None:
        logger.info(f"[BRIDGE-D2] (sin Azure) {json.dumps(payload, ensure_ascii=False)}")
        return
    try:
        msg = Message(json.dumps(payload))
        msg.content_encoding = "utf-8"
        msg.content_type = "application/json"
        client.send_message(msg)
        logger.info(
            f"[BRIDGE-D2] Reenviado a IoT Central: "
            f"temp={payload.get('temperature')} hum={payload.get('humidity')} lux={payload.get('lux')}"
        )
    except Exception as e:
        logger.error(f"[BRIDGE-D2] Error enviando a IoT Central: {e}")
        _azure_client = None  # forzar reconexión en próximo mensaje


def on_message(client, userdata, msg):
    """Callback al recibir mensaje de Wokwi."""
    try:
        raw = msg.payload.decode("utf-8")
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.warning(f"[BRIDGE-D2] Mensaje inválido ignorado: {e}")
        return

    # Agregar metadatos del bridge
    payload["_bridge"] = "wokwi-to-iotcentral"
    payload["_source"] = "wokwi_D2"           # corregido: faltaba el = original
    payload["_timestamp"] = datetime.now(timezone.utc).isoformat()

    forward_to_azure(payload)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"[BRIDGE-D2] Conectado a broker {WOKWI_BROKER}:{WOKWI_PORT}")
        client.subscribe(WOKWI_TOPIC)
        logger.info(f"[BRIDGE-D2] Suscrito a {WOKWI_TOPIC} — esperando mensajes Wokwi...")
    else:
        logger.error(f"[BRIDGE-D2] Fallo de conexión MQTT: código {rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"[BRIDGE-D2] Desconexión inesperada: código {rc} — reintentando...")


def start_bridge():
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=f"bridge-{DEVICE_ID}")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    # Reconexión automática
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)

    try:
        mqtt_client.connect(WOKWI_BROKER, WOKWI_PORT, keepalive=60)
        logger.info(f"[BRIDGE-D2] Conectando a {WOKWI_BROKER}:{WOKWI_PORT}...")
        mqtt_client.loop_forever()
    except KeyboardInterrupt:
        logger.info("[BRIDGE-D2] Detenido por usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"[BRIDGE-D2] Error crítico: {e}")
    finally:
        try:
            mqtt_client.disconnect()
        except Exception:
            pass
        global _azure_client
        if _azure_client is not None:
            try:
                _azure_client.disconnect()
                logger.info("[BRIDGE-D2] Azure IoT Central desconectado")
            except Exception as e:
                logger.warning(f"[BRIDGE-D2] Error al desconectar Azure: {e}")


if __name__ == "__main__":
    logger.info("[BRIDGE-D2] Iniciando bridge Wokwi → Azure IoT Central")
    logger.info(f"[BRIDGE-D2] Broker: {WOKWI_BROKER}:{WOKWI_PORT}")
    logger.info(f"[BRIDGE-D2] Tópico Wokwi: {WOKWI_TOPIC}")
    logger.info(f"[BRIDGE-D2] Dispositivo IoT Central: {DEVICE_ID}")
    start_bridge()
