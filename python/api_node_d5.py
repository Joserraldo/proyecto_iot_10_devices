#!/usr/bin/env python3
"""
D5 - Calidad aire aula
-----------------------
Origen: API Pública (Open-Meteo — datos meteorológicos reales)
Protocolo: HTTPS (API) + MQTT/TLS (envío a IoT Central)
Intervalo: 15 segundos

VARIABLES:
  Desde Open-Meteo (reales):
    temperature, humidity, wind_speed, wind_direction
  Simuladas (etiquetadas como tal, Open-Meteo no provee CO2/PM):
    co2_sim, pm25_sim, pm10_sim

NOTA: Open-Meteo forecast no incluye CO2 ni PM2.5/PM10.
      Esas variables se simulan con valores realistas de aula universitaria.
      Si se conecta a un sensor real o API especializada (IQAir, WAQI, etc.),
      reemplazar simulate_indoor_air_quality() con la llamada real.
"""

import os
import time
import json
import random
import logging
import requests
from datetime import datetime, timezone
from azure.iot.device import IoTHubDeviceClient, Message

# Credenciales Azure
CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D5", "campus-ems-05")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D5", "15"))

# Open-Meteo (sin API key, gratuito)
OPEN_METEO_URL = os.getenv(
    "OPEN_METEO_API_URL",
    "https://api.open-meteo.com/v1/forecast",
)
LATITUDE = os.getenv("LATITUDE", "7.1254")    # Bucaramanga, Colombia (UNAB)
LONGITUDE = os.getenv("LONGITUDE", "-73.1198")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D5] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Cliente Azure persistente para evitar reconectar cada ciclo
_azure_client = None


def get_azure_client():
    global _azure_client
    if _azure_client is not None:
        return _azure_client
    if not CONNECTION_STRING:
        return None
    try:
        _azure_client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
        _azure_client.connect()
        logger.info(f"[D5] {DEVICE_ID} conectado a IoT Central")
    except Exception as e:
        logger.error(f"[D5] Error al conectar: {e}")
        _azure_client = None
    return _azure_client


def fetch_open_meteo():
    """Obtiene temperatura, humedad y viento desde Open-Meteo (datos reales)."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        current = data.get("current", {})
        return {
            "temperature": round(float(current.get("temperature_2m", 25.0)), 1),
            "humidity": round(float(current.get("relative_humidity_2m", 60.0)), 1),
            "wind_speed": round(float(current.get("wind_speed_10m", 5.0)), 1),
            "wind_direction": round(float(current.get("wind_direction_10m", 180.0)), 1),
            "api_source": "open-meteo-real",
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"[D5] Open-Meteo no disponible: {e} — usando fallback")
        return {
            "temperature": round(25.0 + random.uniform(-3, 3), 1),
            "humidity": round(random.uniform(40, 70), 1),
            "wind_speed": round(random.uniform(0, 10), 1),
            "wind_direction": round(random.uniform(0, 360), 1),
            "api_source": "fallback-simulated",
        }
    except Exception as e:
        logger.error(f"[D5] Error inesperado Open-Meteo: {e}")
        return {
            "temperature": 25.0,
            "humidity": 60.0,
            "wind_speed": 5.0,
            "wind_direction": 180.0,
            "api_source": "fallback-simulated",
        }


def simulate_indoor_air_quality():
    """
    CO2 y PM simulados con patrones de aula universitaria.
    REEMPLAZAR con API real (IQAir, WAQI, SIATA) si se dispone de credenciales.
    """
    hour = datetime.now().hour
    # CO2 más alto en horas de clase (7-12, 14-18)
    in_class = 7 <= hour <= 12 or 14 <= hour <= 18
    co2_base = 900 if in_class else 500
    return {
        "co2_sim": random.randint(co2_base - 100, co2_base + 300),   # ppm
        "pm25_sim": round(random.uniform(5.0, 25.0), 1),             # μg/m³
        "pm10_sim": round(random.uniform(10.0, 50.0), 1),            # μg/m³
    }


def build_telemetry():
    meteo = fetch_open_meteo()
    air = simulate_indoor_air_quality()
    return {
        **meteo,
        **air,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def main():
    logger.info("[D5] Iniciando — Calidad aire aula (Open-Meteo + sim indoor)")
    logger.info(f"[D5] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s")
    logger.info("[D5] temperature/humidity/wind: Open-Meteo real")
    logger.info("[D5] co2_sim/pm25_sim/pm10_sim: simulados (etiqueta _sim)")

    iteration = 0
    try:
        while True:
            iteration += 1
            telemetry = build_telemetry()

            client = get_azure_client()
            if client is not None:
                try:
                    msg = Message(json.dumps(telemetry))
                    msg.content_encoding = "utf-8"
                    msg.content_type = "application/json"
                    client.send_message(msg)
                    if iteration == 1 or iteration % 10 == 0:
                        logger.info(
                            f"[D5] iter={iteration} temp={telemetry['temperature']}°C "
                            f"CO2={telemetry['co2_sim']}ppm src={telemetry['api_source']}"
                        )
                    else:
                        logger.debug(f"[D5] iter={iteration} enviado")
                except Exception as e:
                    logger.error(f"[D5] Error enviando iter={iteration}: {e}")
                    global _azure_client
                    _azure_client = None   # forzar reconexión en próximo ciclo
            else:
                # Modo sin Azure: imprimir en consola
                if iteration == 1 or iteration % 10 == 0:
                    logger.info(f"[D5] (sin Azure) {json.dumps(telemetry, ensure_ascii=False)}")

            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D5] Detenido por usuario (Ctrl+C)")
    finally:
        if _azure_client is not None:
            try:
                _azure_client.disconnect()
                logger.info("[D5] Desconectado")
            except Exception as e:
                logger.warning(f"[D5] Error al desconectar: {e}")


if __name__ == "__main__":
    main()
