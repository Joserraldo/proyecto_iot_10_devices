#!/usr/bin/env python3
# MQTT Bridge - Wokwi to Azure IoT Central
# Este script actúa como puente entre Wokwi (MQTT local) y Azure IoT Central
# Recibe datos del simulador Wokwi y los reenvía a IoT Central

import os
import json
import time
import logging
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message

# Configuración Wokwi (local)
WOKWI_MQTT_BROKER = os.getenv("WOKWI_MQTT_BROKER", "localhost")
WOKWI_MQTT_PORT = int(os.getenv("WOKWI_MQTT_PORT", "1883"))
WOKWI_MQTT_TOPIC = os.getenv("WOKWI_MQTT_TOPIC", "wokui/campus/ems/D2")

# Configuración Azure IoT Central
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
AZURE_DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D2", "campus-ems-02")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [BRIDGE] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def on_wokwi_message(client, userdata, message):
    """Callback cuando Wokwi publica un mensaje."""
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        logger.debug(f"Mensaje recibido de Wokwi: {payload}")
        
        # Transformar y reenviar a IoT Central
        if IOT_CENTRAL_CONNECTION_STRING:
            azure_client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
            azure_client.connect()
            
            # Agregar metadatos del puente
            payload["_bridge"] = "wokwi-to-iotcentral"
            payload["_source"] "wokwi_D2"
            payload["_timestamp"] = datetime.now(timezone.utc).isoformat()
            
            msg = Message(json.dumps(payload))
            msg.content_encoding = "utf-8"
            msg.content_type = "application/json"
            
            azure_client.send_message(msg)
            logger.info(f"Reenviado a IoT Central: {json.dumps(payload, ensure_ascii=False)}")
            
            azure_client.disconnect()
        else:
            logger.warning("No hay conexión a IoT Central - mensaje descartado")
    except Exception as e:
        logger.error(f"Error procesando mensaje Wokwi: {e}")


def start_bridge():
    """Inicia el puente MQTT."""
    try:
        # Cliente MQTT para subscribirse a Wokwi
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        mqtt_client.on_message = on_wokwi_message
        
        # Conectar al broker Wokwi/local
        mqtt_client.connect(WOKWI_MQTT_BROKER, WOKWI_MQTT_PORT, 60)
        logger.info(f"Conectado al broker MQTT Wokwi: {WOKWI_MQTT_BROKER}:{WOKWI_MQTT_PORT}")
        
        # Suscribirse al tópico de Wokwi
        mqtt_client.subscribe(WOKWI_MQTT_TOPIC)
        logger.info(f"Suscripto al tópico: {WOKWI_MQTT_TOPIC}")
        
        # Loop infinitos
        mqtt_client.loop_forever()
        
    except Exception as e:
        logger.error(f"Error crítico en el puente: {e}")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Iniciando Bridge Wokwi -> Azure IoT Central")
    logger.info("=" * 60)
    logger.info(f"Dispositivo D2: campus-ems-02 (Meteo patio/cubierta)")
    logger.info(f"Broker Wokwi: {WOKWI_MQTT_BROKER}:{WOKWI_MQTT_PORT}")
    logger.info(f"Tópico subscripción: {WOKWI_MQTT_TOPIC}")
    logger.info("Función: Recibir datos Wokwi y reenviar a IoT Central")
    logger.info("=" * 60)
    
    start_bridge()