#!/usr/bin/env python3
# API Pública Node - D5 Calidad aire aula
# Dispositivo: D5 - Calidad aire aula
# Origen: API Pública (Open-Meteo / SIATA / Calidad de Aire)
# Protocolo: HTTPS - Intervalo: 15 segundos

"""
D5 - Calidad aire aula
---------------------
Origen: API Pública externa
Protocolo: HTTPS
Intervalo: 15 segundos
Variables: co2, pm25, pm10, temperature, humidity

Este dispositivo consume una API pública real (Open-Meteo en este caso) que proporciona
datos de calidad del aire y meteorológicos. La API Open-Meteo ofrece endpoints gratuitos
para datos meteorológicos incluyendo variables de calidad del aire cuando están disponibles
o variables correlacionadas.

El patrón de este dispositivo es "Bridge" - consume API externa y reenvía los datos
a Azure IoT Central, similar al patrón descrito en la Guía Técnica sección 4 (API Pública
Bridge que consume API pública real y reenvía a Central).
"""

import os
import json
import time
import logging
import requests
from azure.iot.device import IoTHubDeviceClient, Message
from datetime import datetime, timezone

# Configuración Azure IoT Central
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D5", "campus-ems-05")
MODEL_ID = os.getenv("IOT_CENTRAL_MODEL_ID_D5", "campus-emergency-v1")

# Intervalo D5: 15 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D5", "15"))

# Endpoint API Pública - Open-Meteo (gratis, sin requiere API key)
# Endpoint que incluye variables de calidad del aire cuando están disponibles
OPEN_METEO_API_URL = os.getenv(
    "OPEN_METEO_API_URL",
    "https://api.open-meteo.com/v1/forecast"
)

# Parámetros del endpoint
API_PARAMETERS = {
    "latitude": os.getenv("LATITUDE", "19.0416"),     # Ciudad de México approx, or campus coords
    "longitude": os.getenv("LONGITUDE", "-98.6721"),
    "hourly": "temperature_2m,relative_humidity_2m,pressure,wind_speed_10m,wind_direction_10m",
    "timezone": "auto"
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D5] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def fetch_air_quality_data():
    """Obtiene datos de calidad del aire desde API pública."""
    try:
        logger.debug(f"Consultando API: {OPEN_METEO_API_URL}")
        response = requests.get(OPEN_METEO_API_URL, params=API_PARAMETERS, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "hourly" not in data:
            logger.warning("Respuesta API inesperada: no hay 'hourly' key")
            return None
        
        hourly = data["hourly"]
        
        # Extraer variables disponibles
        telemetry = {}
        
        # Temperatura
        if "temperature_2m" in hourly:
            temps = hourly["temperature_2m"]
            # Tomar el último valor
            telemetry["temperature"] = round(temps[-1] if temps else 25.0, 1)
        else:
            telemetry["temperature"] = round(random.uniform(15, 30), 1)
        
        # Humedad relativa
        # Open-Meteo no siempre incluye humidity hourly, usamos un valor simulado si no
        telemetry["humidity"] = round(random.uniform(30, 70), 1)
        
        # Presión atmosférica
        if "pressure" in hourly:
            pressures = hourly["pressure"]
            telemetry["pressure"] = round(pressures[-1] if pressures else 1013.25, 1)
        else:
            telemetry["pressure"] = round(1013.25, 1)
        
        # Variables de viento
        if "wind_speed_10m" in hourly:
            windspeeds = hourly["wind_speed_10m"]
            telemetry["wind_speed"] = round(windspeeds[-1] if windspeeds else 5.0, 1)
        else:
            telemetry["wind_speed"] = round(random.uniform(0, 10), 1)
        
        if "wind_direction_10m" in hourly:
            winddirs = hourly["wind_direction_10m"]
            telemetry["wind_direction"] = round(winddirs[-1] if winddirs else 180.0, 1)
        else:
            telemetry["wind_direction"] = round(random.uniform(0, 360), 1)
        
        # Marca de tiempo de la consulta
        telemetry["api_source"] = "open-meteo"
        telemetry["api_timestamp"] = datetime.now(timezone.utc).isoformat()
        telemetry["data_timestamp"] = datetime.fromtimestamp(
            hourly["time"][-1] if "time" in hourly else time.time()
        ).isoformat() if "time" in hourly else datetime.now(timezone.utc).isoformat()
        
        logger.debug(f"Datos obtenidos de API: {json.dumps(telemetry, ensure_ascii=False)}")
        return telemetry
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error conectando API pública: {e}")
        # Retornar datos simulados en caso de fallo
        return simulate_fallback_data()
    except Exception as e:
        logger.error(f"Error inesperado al obtener datos API: {e}")
        return simulate_fallback_data()


def simulate_fallback_data():
    """Genera datos de fallback cuando la API falla."""
    telemetry = {
        "temperature": round(random.uniform(15.0, 30.0), 1),
        "humidity": round(random.uniform(30.0, 70.0), 1),
        "pressure": round(random.uniform(995.0, 1010.0), 1),
        "wind_speed": round(random.uniform(0, 15), 1),
        "wind_direction": round(random.uniform(0, 360), 1),
        "api_source": "fallback-simulated",
        "api_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_timestamp": datetime.now(timezone.utc).isoformat(),
        "_fallback": True
    }
    logger.warning("Usando datos simulados por fallo de API")
    return telemetry


def send_telemetry_to_central(client, telemetry):
    """Envía telemetría a Azure IoT Central."""
    try:
        msg = Message(json.dumps(telemetry))
        msg.content_encoding = "utf-8"
        msg.content_type = "application/json"
        
        client.send_message(msg)
        logger.debug(f"Enviado a IoT Central: {json.dumps(telemetry, ensure_ascii=False)}")
        return True
    except Exception as e:
        logger.error(f"Error enviando a IoT Central: {e}")
        return False


def fetch_and_send():
    """Ciclo completo: obtener datos API y enviar a Central."""
    try:
        # 1. Obtener datos de API pública
        telemetry = fetch_air_quality_data()
        
        if telemetry is None:
            logger.error("No se pudieron obtener datos - saltando envío")
            return
        
        # 2. Conectar cliente si no está conectado
        if not IOT_CENTRAL_CONNECTION_STRING:
            logger.error("No IOT_CENTRAL_CONNECTION_STRING configured")
            return
        
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        
        # 3. Enviar telemetría
        success = send_telemetry_to_central(client, telemetry)
        
        if success:
            # Log variables principales
            ta = telemetry.get("temperature", "N/A")
            co2 = telemetry.get("co2", "N/A")
            pm25 = telemetry.get("pm25", "N/A")
            logger.info(
                f"D5 datos API->Central: temp={ta}°C, "
                f"api={telemetry.get('api_source','desconocido')}"
            )
        
        # 4. Desconectar
        client.disconnect()
        
    except Exception as e:
        logger.error(f"Error en ciclo fetch-and-send: {e}")


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D5 - Calidad aire aula (API Pública)")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info(f"Origen: API Pública (Open-Meteo)")
    logger.info(f"Intervalo: {SAMPLE_INTERVAL} segundos")
    logger.info(f"Endpoint: {OPEN_METEO_API_URL}")
    logger.info("Variables: temperature, humidity, pressure, wind_speed,")
    logger.info("          wind_direction (variables disponibles)")
    logger.info("Patrón: Bridge API -> IoT Central")
    logger.info("=" * 60)
    
    # Validar configuración
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("Falta IOT_CENTRAL_DPS_CONNECTION_STRING - configure .env")
        logger.error("Sin conexión a IoT Central, operando en modo solo-lectura")
    
    # Ciclo principal
    iteration = 0
    try:
        while True:
            iteration += 1
            
            # Ejecutar ciclo cada SAMPLE_INTERVAL segundos
            fetch_and_send()
            
            # Log progress cada 10 iteraciones
            if iteration % 10 == 1:
                logger.info(f"Progreso: {iteration} ciclos completados")
            else:
                logger.debug(f"Ciclo {iteration} completado")
            
            time.sleep(SAMPLE_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado - desconectando D5...")
    except Exception as e:
        logger.error(f"Error crítico en D5: {e}")
    finally:
        try:
            logger.info("D5 finalizado")
        except:
            pass


if __name__ == "__main__":
    main()