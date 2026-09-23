#!/usr/bin/env python3
"""
Bridge MQTT — Wokwi → Azure IoT Central (D2)
----------------------------------------------
Escucha lo que publica el simulador Wokwi (ESP32 D2) y hace dos cosas:

  1. campus/ems/D2      → telemetría JSON: la reenvía a Azure IoT Central
                          y registra la línea ``[D2] TELE {...}`` (la que el
                          dashboard usa para el histórico de D2).
  2. campus/ems/D2/log  → logs de texto (lo mismo que el Serial Monitor):
                          los agrega con marca de tiempo a
                          ``~/iotlogs/wokwi_d2.log``, que el dashboard muestra
                          en el panel "Wokwi D2 · Serial en vivo".

Así las evidencias del simulador quedan en la VM aunque Wokwi corra en otro equipo.

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
# El bridge se suscribe a todo el árbol para recibir también el sub-tópico de logs
WOKWI_SUB = WOKWI_TOPIC.rstrip("/") + "/#"
LOG_TOPIC = WOKWI_TOPIC.rstrip("/") + "/log"

# Azure IoT Central
CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D2", "campus-ems-02")

# Archivo de logs del simulador (lo lee el dashboard)
LOG_DIR = os.getenv("LOG_DIR") or os.path.expanduser("~/iotlogs")
WOKWI_LOG = os.path.join(LOG_DIR, "wokwi_d2.log")
LOG_ROTATE_BYTES = int(os.getenv("WOKWI_LOG_ROTATE_BYTES", str(5 * 1024 * 1024)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRIDGE-D2] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Cliente Azure persistente (se crea una vez, no por mensaje)
_azure_client = None
_log_stats = {"lines": 0, "bytes": 0}


# ------------------------------------------------------------------ log Wokwi
def _rotate_if_needed():
    try:
        if os.path.getsize(WOKWI_LOG) > LOG_ROTATE_BYTES:
            os.replace(WOKWI_LOG, WOKWI_LOG + ".1")
    except OSError:
        pass


def append_wokwi_log(line: str):
    """Guarda una línea del Serial de Wokwi con marca de tiempo."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{stamp} | {line}\n"
    try:
        _rotate_if_needed()
        with open(WOKWI_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
        _log_stats["lines"] += 1
        _log_stats["bytes"] += len(entry.encode("utf-8"))
    except OSError as e:
        logger.warning(f"[BRIDGE-D2] no se pudo escribir {WOKWI_LOG}: {e}")


# ------------------------------------------------------------------ Azure
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
        logger.info(f"[D2] TELE {json.dumps(payload)}")
        logger.info(
            f"[BRIDGE-D2] Reenviado a IoT Central: "
            f"temp={payload.get('temperature')} hum={payload.get('humidity')} lux={payload.get('lux')}"
        )
    except Exception as e:
        logger.error(f"[BRIDGE-D2] Error enviando a IoT Central: {e}")
        _azure_client = None  # forzar reconexión en próximo mensaje


# ------------------------------------------------------------------ MQTT
def on_message(client, userdata, msg):
    """Callback al recibir mensaje de Wokwi (telemetría o log)."""
    try:
        raw = msg.payload.decode("utf-8", "replace")
    except Exception as e:  # pragma: no cover
        logger.warning(f"[BRIDGE-D2] payload ilegible en {msg.topic}: {e}")
        return

    topic = msg.topic or ""

    # ---- logs del Serial Monitor ----
    if topic == LOG_TOPIC or topic.endswith("/log"):
        for line in raw.splitlines():
            line = line.strip()
            if line:
                append_wokwi_log(line)
        return

    # ---- telemetría ----
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        # Algo que no es JSON ni viene del tópico de logs: lo guardamos como log.
        logger.warning(f"[BRIDGE-D2] Mensaje inválido en {topic} ({e}) — guardado como log")
        append_wokwi_log(f"[{topic}] {raw}")
        return

    payload["_bridge"] = "wokwi-to-iotcentral"
    payload["_source"] = "wokwi_D2"
    payload["_timestamp"] = datetime.now(timezone.utc).isoformat()

    forward_to_azure(payload)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"[BRIDGE-D2] Conectado a broker {WOKWI_BROKER}:{WOKWI_PORT}")
        client.subscribe(WOKWI_SUB)
        logger.info(f"[BRIDGE-D2] Suscrito a {WOKWI_SUB} — esperando mensajes Wokwi...")
    else:
        logger.error(f"[BRIDGE-D2] Fallo de conexión MQTT: código {rc}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        logger.warning(f"[BRIDGE-D2] Desconexión inesperada: código {rc} — reintentando...")


def start_bridge():
    # Compatibilidad paho-mqtt 1.x y 2.x
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=f"bridge-{DEVICE_ID}")
    except AttributeError:  # paho 1.x no tiene CallbackAPIVersion
        mqtt_client = mqtt.Client(client_id=f"bridge-{DEVICE_ID}")
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
    os.makedirs(LOG_DIR, exist_ok=True)
    logger.info("[BRIDGE-D2] Iniciando bridge Wokwi → Azure IoT Central")
    logger.info(f"[BRIDGE-D2] Broker: {WOKWI_BROKER}:{WOKWI_PORT}")
    logger.info(f"[BRIDGE-D2] Tópico Wokwi: {WOKWI_TOPIC}  (logs: {LOG_TOPIC} → {WOKWI_LOG})")
    logger.info(f"[BRIDGE-D2] Dispositivo IoT Central: {DEVICE_ID}")
    start_bridge()
