#!/usr/bin/env python3
# Node SDK Connection - D1 Estación meteo campus
# Dispositivo: D1 - Digital Twin - Intervalo: 15s - Origen: Azure IoT Central

"""
D1 - Estación meteo campus
------------------------
Origen: Digital Twin (simulación interna en IoT Central)
Protocolo: MQTT/TLS por DPS
Intervalo: 15 segundos
Variables: temperature, humidity, pressure, wind_speed, wind_direction, rainfall, timestamp

Este dispositivo representa la estación meteorológica principal del campus.
Usa el Digital Twin nativo de IoT Central, lo que significa que su telemetría
es generada y gestionada internamente por la plataforma.
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone

# Azure IoT SDK
from azure.iot.device import IoTHubDeviceClient, Message

# Configuración desde variables de entorno (NUNCA hardcodeadas)
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D1", "campus-ems-01")
MODEL_ID = os.getenv("IOT_CENTRAL_MODEL_ID_D1", "campus-emergency-v1")

# Intervalo de muestreo D1: 15 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D1", "15"))

# Rangos realistas para estación meteorológica campus
SENSOR_CONFIG = {
    "temperature": {"min": -10, "max": 40, "noise": 0.5, "base": 25.0},
    "humidity": {"min": 20, "max": 80, "noise": 3.0, "base": 60.0},
    "pressure": {"min": 980, "max": 1050, "noise": 1.0, "base": 1013.25},
    "wind_speed": {"min": 0, "max": 50, "noise": 0.5, "base": 5.0},
    "wind_direction": {"min": 0, "max": 360, "noise": 5.0, "base": 180.0},
    "rainfall": {"min": 0, "max": 50, "noise": 0.3, "base": 0.0},
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D1] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def generate_realistic_telemetry():
    """Genera telemetría realista para estación meteorológica."""
    telemetry = {}
    
    # Temperatura con variación diurna simple + ruido
    temp_base = SENSOR_CONFIG["temperature"]["base"] + random.uniform(-5, 5)
    telemetry["temperature"] = round(
        max(SENSOR_CONFIG["temperature"]["min"],
            min(SENSOR_CONFIG["temperature"]["max"], temp_base)),
        1
    )
    
    # Humedad inversamente relacionada con temperatura (simplificado)
    hum_base = SENSOR_CONFIG["humidity"]["base"] - (temp_base - 20) * 0.3
    telemetry["humidity"] = round(
        max(SENSOR_CONFIG["humidity"]["min"],
            min(SENSOR_CONFIG["humidity"]["max"], hum_base + random.uniform(-10, 10))),
        1
    )
    
    # Presión atmosférica con variación mínima
    telemetry["pressure"] = round(
        max(SENSOR_CONFIG["pressure"]["min"],
            min(SENSOR_CONFIG["pressure"]["max"], 
                SENSOR_CONFIG["pressure"]["base"] + random.uniform(-5, 5))),
        1
    )
    
    # Velocidad del viento
    telemetry["wind_speed"] = round(
        max(SENSOR_CONFIG["wind_speed"]["min"],
            min(SENSOR_CONFIG["wind_speed"]["max"],
                SENSOR_CONFIG["wind_speed"]["base"] + random.uniform(-3, 3))),
        1
    )
    
    # Dirección del viento
    telemetry["wind_direction"] = round(
        max(SENSOR_CONFIG["wind_direction"]["min"],
            min(SENSOR_CONFIG["wind_direction"]["max"],
                SENSOR_CONFIG["wind_direction"]["base"] + random.uniform(-20, 20))),
        1
    )
    
    # Precipitación (al 70% probabilidad de 0, en caso contrario llovizna)
    if random.random() > 0.3:
        telemetry["rainfall"] = round(random.uniform(0, 5), 1)
    else:
        telemetry["rainfall"] = 0.0
    
    # Marca de tiempo UTC
    telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    return telemetry


def connect_client():
    """Crea y conecta el cliente IoT Hub."""
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("No IOT_CENTRAL_CONNECTION_STRING environment variable set")
        return None
    
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        logger.info(f"D1 {DEVICE_ID} conectado a Azure IoT Central exitosamente")
        return client
    except Exception as e:
        logger.error(f"Error conectando cliente: {e}")
        return None


def send_periodic_telemetry(client):
    """Envía telemetría periódicamente hasta KeyboardInterrupt."""
    try:
        iteration = 0
        while True:
            try:
                iteration += 1
                telemetry = generate_realistic_telemetry()
                msg = Message(json.dumps(telemetry))
                
                # Configurar propiedades del mensaje
                msg.content_encoding = "utf-8"
                msg.content_type = "application/json"
                
                # Enviar telemetría
                client.send_message(msg)
                
                # Logging cada 10 iteraciones para no saturar
                if iteration % 10 == 0:
                    logger.info(f"Iteración {iteration}: Telemetría enviada - {json.dumps(telemetry, ensure_ascii=False)}")
                else:
                    logger.debug(f"Telemetría enviada: {json.dumps(telemetry, ensure_ascii=False)}")
                
                # Esperar próximo intervalo
                time.sleep(SAMPLE_INTERVAL)
                
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado - desconectando D1...")
    except Exception as e:
        logger.error(f"Error en loop principal: {e}")
    finally:
        try:
            client.disconnect()
            logger.info("D1 desconectado de Azure IoT Central")
        except:
            pass


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D1 - Estación meteo campus")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info(f"Intervalo de muestreo: {SAMPLE_INTERVAL} segundos")
    logger.info("Origen: Digital Twin (IoT Central nativo)")
    logger.info("Variables: temperature, humidity, pressure, wind_speed,")
    logger.info("          wind_direction, rainfall, timestamp")
    logger.info("=" * 60)
    
    # Conectar cliente
    client = connect_client()
    if client is None:
        logger.error("No se pudo establecer conexión - saliendo")
        return
    
    # Enviar telemetría periódica
    logger.info(f"Iniciando envío de telemetría cada {SAMPLE_INTERVAL}s")
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()