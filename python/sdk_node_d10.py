#!/usr/bin/env python3
# Node SDK Connection - D10 Puesto de mando
# Dispositivo: D10 - Digital Twin - Intervalo: 20 segundos

"""
D10 - Puesto de mando
----------------------
Origen: Digital Twin (simulación interna IoT Central)
Protocolo: MQTT/TLS por DPS
Intervalo: 20 segundos (el más corto de la flota)
Variables: estado_agregado, confirmacion_ack, temperatura_promedio

Este dispositivo representa el puesto de mando central del campus, que agrega y
procesa datos de todos los demás dispositivos (D1-D9). Es el centro de toma de
decisiones operativas y su intervalo de 20 segundos es el más frecuente, lo que
demuestra la asincronía requerida en el paralelo.

Características clave:
- Agregación de datos en tiempo real de todos los dispositivos del sistema
- Confirmación de alarmas (ACK) para eventos críticos
- Estado general de la flota (Connected/Disconnected count)
- Toma de decisiones basada en reglas configurables
- Digital Twin nativo de IoT Central (capacidades avanzadas de la plataforma)
- El dispositivo con el intervalo más corto, complementando los intervalos más largos
  (D6 de 5min, D4 de 1min) para demostrar 3+ intervalos distintos
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone

# Configuración - variables de entorno (NUNCA hardcodeadas)
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D10", "campus-ems-10")
MODEL_ID = os.getenv("IOT_CENTRAL_MODEL_ID_D10", "campus-emergency-v1")

# Intervalo D10: 20 segundos (el más corto)
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D10", "20"))

# Agregación de datos - pesos para simular lecturas de dispositivos distintos
DEVICE_WEIGHTS = {
    "D1": 0.15,  # Estación meteo - 15% peso
    "D2": 0.10,  # Meteo patio - 10% peso
    "D3": 0.12,  # Incendio Bloque A - 12% peso
    "D4": 0.10,  # Incendio Laboratorio - 10% peso
    "D5": 0.10,  # Calidad aire aula - 10% peso
    "D6": 0.08,  # Calidad aire exterior - 8% peso
    "D7": 0.08,  # Acceso principal - 8% peso
    "D8": 0.07,  # Cerramiento norte - 7% peso
    "D9": 0.10,  # Evacuación pasillo - 10% peso
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D10] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def generate_aggregated_telemetry():
    """Genera telemetría agregada para el puesto de mando."""
    telemetry = {
        # Estado general de la flota
        "estado_agregado": {
            "total_devices": 10,
            "connected_devices": random.randint(8, 10),
            "disconnected_devices": 10 - random.randint(8, 10),
            "last_boot": datetime.now(timezone.utc).isoformat(),
            "system_health": round(random.uniform(85.0, 100.0), 1)
        },
        
        # Temperatura promedio ponderada de todos los dispositivos
        "temperatura_promedio": round(
            random.uniform(18.0, 28.0) + 
            random.uniform(-2.0, 2.0)  # pequeña variación
        , 1),
        
        # Confirmación de alarmas ACK pendientes
        "confirmacion_ack": random.choice([
            {"pending": 0, "total": 5, "status": "all_clear"},
            {"pending": 1, "total": 5, "status": "active_alert"},
            {"pending": 2, "total": 5, "status": "minor_issues"}
        ]),
        
        # Métricas de sistema
        "system_uptime": round(random.uniform(95.0, 100.0), 1),
        "mqtt_connection_status": random.choice(["connected", "connected", "connected", "reconnecting"]),
        
        # Marca de tiempo
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device_role": "command_center",
        "active_zones": random.sample(["campus", "laboratorio", "bloque_a", "patio", "perimetro"], 
                                     k=random.randint(3, 5))
    }
    
    return telemetry


def connect_client():
    """Conecta cliente IoT Hub para D10."""
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("No IOT_CENTRAL_CONNECTION_STRING environment variable set")
        return None
    
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        logger.info(f"D10 {DEVICE_ID} conectado a Azure IoT Central")
        return client
    except Exception as e:
        logger.error(f"Error conectando cliente D10: {e}")
        return None


def send_periodic_telemetry(client):
    """Envía telemetría agregada cada 20 segundos."""
    try:
        iteration = 0
        while True:
            try:
                iteration += 1
                telemetry = generate_aggregated_telemetry()
                
                msg = Message(json.dumps(telemetry))
                msg.content_encoding = "utf-8"
                msg.content_type = "application/json"
                
                client.send_message(msg)
                
                # Logging cada 5 iteraciones (100 segundos)
                if iteration % 5 == 1:
                    connected = telemetry["estado_agregado"]["connected_devices"]
                    ack_status = telemetry["confirmacion_ack"]["status"]
                    avg_temp = telemetry["temperatura_promedio"]
                    logger.info(
                        f"Iteración {iteration}: flota conectadas={connected}/10, "
                        f"ACK status={ack_status}, temp_prom={avg_temp}°C"
                    )
                else:
                    logger.debug(f"Telemetría agregada enviada: estado flock summary")
                
                time.sleep(SAMPLE_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Interrupción por teclado - desconectando D10...")
                break
            except Exception as e:
                logger.error(f"Error en loop principal D10: {e}")
                time.sleep(5)
        
        finally:
            try:
                client.disconnect()
                logger.info("D10 desconectado de Azure IoT Central")
            except:
                pass


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D10 - Puesto de mando")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info("Origen: Digital Twin (IoT Central nativo)")
    logger.info("Intervalo: 20 segundos (el más corto de la flota)")
    logger.info("Funcionalidad: Agregación de datos, ACK de alarmas, toma decisiones")
    logger.info("Demuestra: 3+ intervalos distintos (20s vs 1min vs 5min)")
    logger.info("=" * 60)
    
    client = connect_client()
    if client is None:
        logger.error("No se pudo establecer conexión - saliendo")
        return
    
    logger.info(f"Iniciando envío de telemetría agregada cada {SAMPLE_INTERVAL}s")
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()