#!/usr/bin/env python3
# API Pública Node - D6 Calidad aire exterior
# Dispositivo: D6 - Calidad aire exterior
# Origen: Atlas Weather - Protocolo: HTTPS - Intervalo: 5 minutos

"""
D6 - Calidad aire exterior
-------------------------
Origen: Atlas Weather
Protocolo: HTTPS
Intervalo: 5 minutos (300 segundos)
Variables: pm25, pm10, aqi, temperature, humidity, wind_speed, wind_direction

Este dispositivo consume el servicio Atlas Weather (o API alternativa) para obtener
datos de calidad del aire y condiciones meteorológicas externas. Atlas Weather proporciona
datos más especializados que Open-Meteo para partículas y índices de calidad del aire.

Patrón: Bridge API -> IoT Central (igual que D5, pero con servicio Atlas Weather en lugar
de Open-Meteo, y intervalo diferente de 5 minutos en lugar de 15).
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
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D6", "campus-ems-06")
MODEL_ID = os.getenv("IOT_CENTRAL_MODEL_ID_D6", "campus-emergency-v1")

# Intervalo D6: 5 minutos = 300 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D6", "300"))

# Endpoint Atlas Weather (o alternativa)
# Atlas Weather requiere suscripción, usamos variable de entorno para endpoint
ATLAS_WEATHER_API_URL = os.getenv(
    "ATLAS_WEATHER_API_URL",
    "https://api.atlas.microsoft.com/weather/v2"
)

# Parámetros - variables de calidad aire y meteorología
API_PARAMETERS = {
    "latitude": os.getenv("LATITUDE", "19.0416"),
    "longitude": os.getenv("LONGITUDE", "-98.6721"),
    "parameters": "pm25,pm10,aqi,temperature,humidity,wind_speed,wind_direction,pressure",
    "apikey": os.getenv("ATLAS_API_KEY", "demo-key"),  # Usar key real en .env
    "acquisitionmode": "standard",
    "datasource": "default"
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D6] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def fetch_atlas_weather_data():
    """Obtiene datos de calidad aire desde Atlas Weather."""
    try:
        logger.debug(f"Consultando Atlas Weather: {ATLAS_WEATHER_API_URL}")
        response = requests.get(ATLAS_WEATHER_API_URL, 
                              params=API_PARAMETERS, 
                              timeout=15)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Respuesta Atlas Weather: {json.dumps(data, ensure_ascii=False)[:200]}...")
        
        # Navegar estructura de respuesta Atlas Weather
        telemetry = {}
        
        # La estructura típica Atlas Weather tiene:
        # - value o observations con los parámetros solicitados
        # - location, timestamp, etc.
        
        # Intentar extraer variables comunes
        if "value" in data:
            val = data["value"]
            if isinstance(val, dict):
                # Extraer variables conocidas
                for var in ["pm25", "pm10", "aqi", "temperature", "humidity", 
                           "wind_speed", "wind_direction", "pressure"]:
                    if var in val:
                        telemetry[var] = round(val[var], 1) if isinstance(val[var], (int, float)) else val[var]
                        
        # Si no hay estructura 'value', intentar directo
        if not telemetry:
            # Estructura alternativa
            for var in ["pm25", "pm10", "aqi", "temperature", "humidity", 
                       "wind_speed", "wind_direction", "pressure"]:
                if var in data:
                    telemetry[var] = round(data[var], 1) if isinstance(data[var], (int, float)) else data[var]
        
        # Agregar metadatos
        telemetry["api_source"] = "atlas-weather"
        telemetry["api_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Timestamp de los datos (si está disponible)
        if "timestamp" in data:
            telemetry["data_timestamp"] = data["timestamp"]
        elif "time" in data:
            telemetry["data_timestamp"] = data["time"]
        else:
            telemetry["data_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        logger.debug(f"Datos Atlas Weather: {json.dumps(telemetry, ensure_ascii=False)}")
        return telemetry
        
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "desconocido"
        logger.error(f"Error HTTP Atlas Weather ({status}): {e}")
        return simulate_fallback_data()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión Atlas Weather: {e}")
        return simulate_fallback_data()
    except Exception as e:
        logger.error(f"Error inesperado Atlas Weather: {e}")
        return simulate_fallback_data()


def simulate_fallback_data():
    """Genera datos de fallback cuando Atlas Fallo."""
    telemetry = {
        "pm25": round(random.uniform(0, 50), 1),
        "pm10": round(random.uniform(0, 100), 1),
        "aqi": random.randint(20, 100),
        "temperature": round(random.uniform(-5, 35), 1),
        "humidity": round(random.uniform(20, 80), 1),
        "wind_speed": round(random.uniform(0, 20), 1),
        "wind_direction": round(random.uniform(0, 360), 1),
        "pressure": round(random.uniform(995, 1015), 1),
        "api_source": "fallback-simulated",
        "api_timestamp": datetime.now(timezone.utc).isoformat(),
        "data_timestamp": datetime.now(timezone.utc).isoformat(),
        "_fallback": True
    }
    logger.warning("Usando datos simulados por fallo Atlas Weather")
    return telemetry


def send_telemetry_to_central(client, telemetry):
    """Envía telemetría a Azure IoT Central."""
    try:
        msg = Message(json.dumps(telemetry))
        msg.content_encoding = "utf-8"
        msg.content_type = "application/json"
        
        client.send_message(msg)
        # Log variables clave
        pm25 = telemetry.get("pm25", "N/A")
        aqi = telemetry.get("aqi", "N/A")
        temp = telemetry.get("temperature", "N/A")
        logger.info(f"D6 Atlas->Central: PM2.5={pm25}μg/m³, AQI={aqi}, temp={temp}°C")
        return True
    except Exception as e:
        logger.error(f"Error enviando a IoT Central: {e}")
        return False


def fetch_and_send():
    """Ciclo completo: obtener datos Atlas y enviar a Central."""
    try:
        # 1. Obtener datos de Atlas Weather
        telemetry = fetch_atlas_weather_data()
        
        if telemetry is None:
            logger.error("No se pudieron obtener datos Atlas - saltando envío")
            return
        
        # 2. Conectar y enviar a IoT Central
        if not IOT_CENTRAL_CONNECTION_STRING:
            logger.error("No IOT_CENTRAL_DPS_CONNECTION_STRING configured")
            return
        
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        
        success = send_telemetry_to_central(client, telemetry)
        
        if success:
            logger.debug(f"Telemetría enviada: {json.dumps(telemetry, ensure_ascii=False)}")
        
        # 3. Desconectar
        client.disconnect()
        
    except Exception as e:
        logger.error(f"Error en ciclo fetch-and-send D6: {e}")


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D6 - Calidad aire exterior (Atlas Weather)")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info(f"Origen: Atlas Weather")
    logger.info(f"Intervalo: {SAMPLE_INTERVAL} segundos (5 minutos)")
    logger.info(f"Endpoint: {ATLAS_WEATHER_API_URL}")
    logger.info("Variables: pm25, pm10, aqi, temperature, humidity,")
    logger.info("          wind_speed, wind_direction, pressure")
    logger.info("Patrón: Bridge API -> IoT Central")
    logger.info("Notas: Requiere Atlas API Key en .env para datos reales")
    logger.info("=" * 60)
    
    # Validar configuración crítica
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("Falta IOT_CENTRAL_DPS_CONNECTION_STRING - configure .env")
    
    # Ciclo principal - intervalo largo (5 min)
    iteration = 0
    try:
        while True:
            iteration += 1
            
            logger.debug(f"Iniciando ciclo {iteration} (intervalo de {SAMPLE_INTERVAL}s)")
            
            fetch_and_send()
            
            # Esperar el intervalo completo (5 minutos = 300s)
            # Mostrar cuenta regresiva simplificada
            for remaining in range(int(SAMPLE_INTERVAL), 0, -30):
                if remaining <= 30:
                    logger.debug(f"Esperando {remaining}s para próximo muestreo...")
                time.sleep(30)
                
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado - desconectando D6...")
    except Exception as e:
        logger.error(f"Error crítico en D6: {e}")
    finally:
        logger.info("D6 finalizado")


if __name__ == "__main__":
    main()