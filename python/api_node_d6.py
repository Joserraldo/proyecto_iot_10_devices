#!/usr/bin/env python3
"""
D6 - Calidad aire exterior
---------------------------
Origen: WAQI (World Air Quality Index) — API pública gratuita con token.
        Si no hay token, usa Open-Meteo como alternativa meteorológica
        + datos de calidad de aire simulados, claramente etiquetados.
Protocolo: HTTPS (API) + MQTT/TLS (envío a IoT Central)
Intervalo: 300 segundos (5 minutos)

NOTA: "Atlas Weather" no dispone de API pública accesible sin suscripción Azure Maps.
      Se usa WAQI (https://waqi.info/) que es gratuito con registro en:
        https://aqicn.org/data-platform/token/
      Configurar: WAQI_TOKEN=tu-token-real en .env
      Sin token, el script corre en modo fallback con datos simulados.
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
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D6", "campus-ems-06")
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D6", "300"))

# WAQI — World Air Quality Index (API pública, token gratuito)
WAQI_TOKEN = os.getenv("WAQI_TOKEN", "")            # Dejar vacío = modo fallback
WAQI_STATION = os.getenv("WAQI_STATION", "bucaramanga")  # Nombre de ciudad
WAQI_URL = f"https://api.waqi.info/feed/{WAQI_STATION}/"

# Open-Meteo (fallback meteorológico sin key)
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
LATITUDE = os.getenv("LATITUDE", "7.1254")
LONGITUDE = os.getenv("LONGITUDE", "-73.1198")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D6] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

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
        logger.info(f"[D6] {DEVICE_ID} conectado a IoT Central")
    except Exception as e:
        logger.error(f"[D6] Error al conectar: {e}")
        _azure_client = None
    return _azure_client


def fetch_waqi():
    """Obtiene calidad de aire desde WAQI. Requiere WAQI_TOKEN."""
    if not WAQI_TOKEN:
        logger.debug("[D6] WAQI_TOKEN no configurado — usando fallback")
        return None
    try:
        resp = requests.get(WAQI_URL, params={"token": WAQI_TOKEN}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "ok":
            logger.warning(f"[D6] WAQI status={data.get('status')} — usando fallback")
            return None
        iaqi = data["data"].get("iaqi", {})
        return {
            "aqi": int(data["data"].get("aqi", 0)),
            "pm25": round(float(iaqi.get("pm25", {}).get("v", 0)), 1),
            "pm10": round(float(iaqi.get("pm10", {}).get("v", 0)), 1),
            "temperature": round(float(iaqi.get("t", {}).get("v", 25.0)), 1),
            "humidity": round(float(iaqi.get("h", {}).get("v", 60.0)), 1),
            "wind_speed": round(float(iaqi.get("w", {}).get("v", 5.0)), 1),
            "api_source": "waqi-real",
        }
    except requests.exceptions.RequestException as e:
        logger.warning(f"[D6] WAQI no disponible: {e}")
        return None
    except Exception as e:
        logger.error(f"[D6] Error inesperado WAQI: {e}")
        return None


def fetch_open_meteo_fallback():
    """Fallback meteorológico con Open-Meteo (sin key)."""
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "timezone": "auto",
    }
    try:
        resp = requests.get(OPEN_METEO_URL, params=params, timeout=10)
        resp.raise_for_status()
        current = resp.json().get("current", {})
        return {
            "temperature": round(float(current.get("temperature_2m", 25.0)), 1),
            "humidity": round(float(current.get("relative_humidity_2m", 60.0)), 1),
            "wind_speed": round(float(current.get("wind_speed_10m", 5.0)), 1),
            "wind_direction": round(float(current.get("wind_direction_10m", 180.0)), 1),
        }
    except Exception:
        return {
            "temperature": round(25.0 + random.uniform(-5, 5), 1),
            "humidity": round(random.uniform(30, 70), 1),
            "wind_speed": round(random.uniform(0, 15), 1),
            "wind_direction": round(random.uniform(0, 360), 1),
        }


def build_telemetry():
    """Construye payload priorizando WAQI; si falla, Open-Meteo + sim AQI."""
    waqi_data = fetch_waqi()
    if waqi_data:
        telemetry = waqi_data
    else:
        # Sin WAQI: meteorología de Open-Meteo + AQI simulado
        meteo = fetch_open_meteo_fallback()
        telemetry = {
            **meteo,
            "aqi": random.randint(20, 80),          # simulado
            "pm25": round(random.uniform(5, 35), 1), # simulado μg/m³
            "pm10": round(random.uniform(10, 70), 1),# simulado μg/m³
            "wind_direction": round(random.uniform(0, 360), 1),
            "api_source": "fallback-simulated",
        }
    telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()
    return telemetry


def main():
    logger.info("[D6] Iniciando — Calidad aire exterior")
    logger.info(f"[D6] Device ID: {DEVICE_ID} | Intervalo: {SAMPLE_INTERVAL}s (5 min)")
    if WAQI_TOKEN:
        logger.info(f"[D6] Modo: WAQI real — estación: {WAQI_STATION}")
    else:
        logger.warning("[D6] WAQI_TOKEN no configurado — modo fallback (Open-Meteo + sim AQI)")
        logger.warning("[D6] Para datos reales: registrar en https://aqicn.org/data-platform/token/")

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
                    logger.info(f"[D6] TELE {json.dumps(telemetry)}")
                    logger.info(
                        f"[D6] iter={iteration} PM2.5={telemetry['pm25']}μg/m³ "
                        f"AQI={telemetry['aqi']} src={telemetry['api_source']}"
                    )
                except Exception as e:
                    logger.error(f"[D6] Error enviando iter={iteration}: {e}")
                    global _azure_client
                    _azure_client = None
            else:
                logger.info(f"[D6] (sin Azure) {json.dumps(telemetry, ensure_ascii=False)}")

            time.sleep(SAMPLE_INTERVAL)
    except KeyboardInterrupt:
        logger.info("[D6] Detenido por usuario (Ctrl+C)")
    finally:
        if _azure_client is not None:
            try:
                _azure_client.disconnect()
                logger.info("[D6] Desconectado")
            except Exception as e:
                logger.warning(f"[D6] Error al desconectar: {e}")


if __name__ == "__main__":
    main()
