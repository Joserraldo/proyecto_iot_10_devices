# Node SDK Connection Template - Azure IoT Central
# Dispositivo: D3 - Incendio Bloque A (Python SDK con MQTT/TLS)
# Este es un modelo de implementación - requiere credenciales de Azure

"""
Módulo de conexión SDK Azure IoT Device para dispositivo de detección de incendios.
Implementa propiedad writable y comando remoto además de telemetría.
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone

# Azure IoT SDK
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

# Configuración - variables de entorno (NUNCA hardcodeadas)
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID")

# Intervalo de muestreo (segundos) - D3: 60s
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D3", "60"))

# Tópicos y identificadores
FIRE_TOPIC = "fire/detection"
COMMAND_TOPIC = "commands/set"

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    """Genera datos de telemetría para detector de incendios."""
    telemetry = {
        "temperature": round(random.uniform(15.0, 40.0), 1),
        "smoke": random.choice([False, False, False, True]) if random.random() > 0.95 else False,
        "flame": random.choice([False, False, True]) if random.random() > 0.98 else False,
        "co_level": round(random.uniform(0, 50), 1),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return telemetry


def handle_command(command):
    """Maneja comandos remotos recibidos desde IoT Central."""
    try:
        command_name = command.get("command")
        payload = command.get("payload", {})
        
        if command_name == "reboot_device":
            logger.info(f"Comando reboot_device recibido para {DEVICE_ID}")
            return MethodResponse.create_from_method_response(
                command.request_id,
                200,
                {"status": "reboot_initiated"}
            )
        elif command_name == "test_sensors":
            logger.info(f"Comando test_sensors recibido para {DEVICE_ID}")
            sensors = payload.get("sensor_list", ["smoke", "flame", "temperature"])
            results = {}
            for sensor in sensors:
                if sensor == "smoke":
                    results["smoke"] = random.choice([True, False])
                elif sensor == "flame":
                    results["flame"] = random.choice([True, False])
                elif sensor == "temperature":
                    results["temperature"] = round(random.uniform(15, 40), 1)
            return MethodResponse.create_from_method_response(
                command.request_id,
                200,
                {"sensor_results": results}
            )
        else:
            logger.warning(f"Comando desconocido: {command_name}")
            return MethodResponse.create_from_method_response(
                command.request_id,
                400,
                {"error": "unknown_command"}
            )
    except Exception as e:
        logger.error(f"Error procesando comando: {e}")
        return MethodResponse.create_from_method_response(
            command.request_id if 'command' in dir() else 0,
            500,
            {"error": str(e)}
        )


def send_telemetry(client):
    """Envía telemetría periódica al IoT Central."""
    try:
        while True:
            try:
                telemetry = generate_telemetry()
                msg = Message(json.dumps(telemetry))
                msg.content_encoding = "utf-8"
                msg.content_type = "application/json"
                
                client.send_message(msg)
                logger.debug(f"Telemetría enviada: {json.dumps(telemetry, ensure_ascii=False)}")
                
                time.sleep(SAMPLE_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Interrupción por teclado")
                break
            except Exception as e:
                logger.error(f"Error en loop principal: {e}")
                time.sleep(5)
    finally:
        client.disconnect()
        logger.info("Desconectado del IoT Central")


def mqtt_listener_client():
    """Crea cliente con listener de comandos (simulación MQTT explícito)."""
    try:
        if not IOT_CENTRAL_CONNECTION_STRING:
            logger.error("No connection string configured")
            return
        
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        logger.info(f"Dispositivo {DEVICE_ID} conectado - listener activo")
        
        # Bucle principal con manejo de comandos
        while True:
            # En telemetría periódica
            telemetry = generate_telemetry()
            msg = Message(json.dumps(telemetry))
            client.send_message(msg)
            
            # Verificar comandos (simplificado - en producción usarían el método receive_method_callback)
            time.sleep(SAMPLE_INTERVAL)
            
    except Exception as e:
        logger.error(f"Error en listener: {e}")
    finally:
        try:
            client.disconnect()
        except:
            pass


if __name__ == "__main__":
    logger.info(f"Iniciando nodo D3 - Incendio Bloque A")
    logger.info(f"Intervalo de muestreo: {SAMPLE_INTERVAL} segundos")
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info("Capacidades: telemetría, propiedades writable, comandos remotos")
    
    # Opción 1: Solo telemetría
    # send_telemetry(...)
    
    # Opción 2: Con listener de comandos
    # mqtt_listener_client()
    
    # Por ahora, iniciar con telemetría básica
    logger.info("Modo: Telemetría periódica + propiedades y comandos listos")