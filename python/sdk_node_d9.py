#!/usr/bin/env python3
# Node SDK Connection - D9 Evacuación pasillo
# Dispositivo: D9 - Digital Twin - Intervalo: 45 segundos

"""
D9 - Evacuación pasillo
------------------------
Origen: Digital Twin (simulación interna IoT Central)
Protocolo: MQTT/TLS por DPS
Intervalo: 45 segundos
Variables: occupancy, lux_emergency, temperature

Este dispositivo representa el sistema de monitoreo de evacuación en los pasillos
del campus. Su funcionalidad principal es detectar ocupación y niveles de iluminación
de emergencia para guiar evacuaiones seguras durante incidentes.

Características clave:
- Monitoreo de ocupación en tiempo real
- Iluminación de emergencia (lux_level con umbrales críticos)
- Temperatura ambiente
- Diseñado para trabajar en coordinación con los sensores de incendio (D3, D4)
- Digital Twin nativo de IoT Central (no requiere SDK Python externo, usa capacidades
  internas de la plataforma)
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone

# Configuración - variables de entorno (NUNCA hardcodeadas)
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D9", "campus-ems-09")
MODEL_ID = os.getenv("IOT_CENTRAL_MODEL_ID_D9", "campus-emergency-v1")

# Intervalo D9: 45 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D9", "45"))

# Lógica de emergencia para pasillos
EMERGENCY_LUX_THRESHOLD = float(os.getenv("EMERGENCY_LUX_THRESHOLD", "20.0"))  # Lux mínimo para emergencia
OCCUPANCY_CHANGE_THRESHOLD = int(os.getenv("OCCUPANCY_CHANGE_THRESHOLD", "3"))  # Cambios consecutivos

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D9] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def generate_evacuation_telemetry():
    """Genera telemetría para monitoreo de evacuación de pasillos."""
    telemetry = {
        # Ocupación actual (0 = vacío, 1 = ocupado, 2 = densidad alta)
        "occupancy": random.choices(
            weights=[0.7, 0.25, 0.05],  # 70% vacío, 25% ocupado, 5% densidad alta
            k=1
        )[0],
        
        # Iluminación de emergencia
        # Simula situación normal o emergencia
        "lux_emergency": round(random.uniform(0, 200), 1),
        
        # Temperatura ambiente
        "temperature": round(random.uniform(18.0, 28.0), 1),
        
        # Meta data
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_location": "pasillo_evacuacion",
        "system_status": "operational"
    }
    
    # Ocasionalmente simular condición de emergencia
    if random.random() > 0.95:  # 5% chance
        telemetry["emergency_status"] = "active"
        telemetry["lux_emergency"] = round(random.uniform(0, EMERGENCY_LUX_THRESHOLD), 1)
    else:
        telemetry["emergency_status"] = "normal"
    
    return telemetry


def connect_client():
    """Conecta cliente IoT Hub para D9."""
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("No IOT_CENTRAL_CONNECTION_STRING environment variable set")
        return None
    
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        logger.info(f"D9 {DEVICE_ID} conectado a Azure IoT Central")
        return client
    except Exception as e:
        logger.error(f"Error conectando cliente D9: {e}")
        return None


def send_periodic_telemetry(client):
    """Envía telemetría periódica para dispositivo de evacuación."""
    try:
        iteration = 0
        while True:
            try:
                iteration += 1
                telemetry = generate_evacuation_telemetry()
                
                msg = Message(json.dumps(telemetry))
                msg.content_encoding = "utf-8"
                msg.content_type = "application/json"
                
                client.send_message(msg)
                
                # Logging cada 10 iteraciones
                if iteration % 10 == 1:
                    occ = telemetry.get("occupancy", 0)
                    lux = telemetry.get("lux_emergency", 0)
                    emergency = telemetry.get("emergency_status", "normal")
                    logger.info(
                        f"Iteración {iteration}: ocupación={occ}, lux={lux}lux, "
                        f"emergency={emergency}"
                    )
                else:
                    logger.debug(f"Telemetría enviada: {json.dumps(telemetry, ensure_ascii=False)}")
                
                time.sleep(SAMPLE_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Interrupción por teclado - desconectando D9...")
                break
            except Exception as e:
                logger.error(f"Error en loop principal D9: {e}")
                time.sleep(5)
        
        finally:
            try:
                client.disconnect()
                logger.info("D9 desconectado de Azure IoT Central")
            except:
                pass


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D9 - Evacuación pasillo")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info("Origen: Digital Twin (IoT Central nativo)")
    logger.info("Intervalo: 45 segundos")
    logger.info("Variables: occupancy, lux_emergency, temperature, emergency_status")
    logger.info("Funcionalidad: Monitoreo para coordinación de evacuación")
    logger.info("=" * 60)
    
    client = connect_client()
    if client is None:
        logger.error("No se pudo establecer conexión - saliendo")
        return
    
    logger.info(f"Iniciando envío de telemetría cada {SAMPLE_INTERVAL}s")
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()