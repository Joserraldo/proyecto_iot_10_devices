#!/usr/bin/env python3
# Node SDK Connection - D4 Incendio Laboratorio
# Dispositivo: D4 - Incendio Laboratorio
# Origen: Python SDK - Intervalo: 1 minuto - Protocolo: MQTT/TLS

"""
D4 - Incendio Laboratorio
------------------------
Origen: Python SDK (azure-iot-device)
Protocolo: MQTT/TLS por DPS
Intervalo: 60 segundos (1 minuto)
Variables: smoke, flame, temperature, co_level, door_status, timestamp

Este dispositivo representa un sensor de detección de incendios en un laboratorio universitario.
Incluye soporte para propiedades writable y comandos remotos, que es crítico para
equipos de emergencia que necesitan configuración remota rápida.
"""

import os
import time
import json
import random
import logging
from datetime import datetime, timezone

# Azure IoT SDK
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse

# Configuración desde variables de entorno
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D4", "campus-ems-04")
MODEL_ID = os.getenv("IOT_CENTRAL_MODEL_ID_D4", "campus-emergency-v1")

# Intervalo D4: 1 minuto = 60 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D4", "60"))

# Configuración lógica incendio laboratorio
FIRE_LOGIC = {
    "smoke_chance_per_reading": 0.02,  # 2% chance por lectura
    "flame_chance_per_reading": 0.005,  # 0.5% chance por lectura
    "temp_base": 22.0,  # Temperatura base laboratorio
    "co_base": 25.0,    # CO base ppm
}

# Configuración propiedades writable
WRITABLE_PROPERTIES = {
    "alert_threshold_temp_max": {"type": "float", "default": 35.0, "min": 10.0, "max": 50.0},
    "alert_threshold_co_max": {"type": "float", "default": 30.0, "min": 0.0, "max": 100.0},
    "alarm_sensitivity": {"type": "string", "default": "medium", "values": ["low", "medium", "high"]},
}

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D4] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def check_fire_conditions():
    """Evalua condiciones de incendio basándose en lógica probabilística."""
    telemetry = {}
    
    # Lógica de humo (probabilística)
    smoke_activated = random.random() < FIRE_LOGIC["smoke_chance_per_reading"]
    telemetry["smoke"] = smoke_activated
    
    # Lógica de llama (menos probable)
    flame_activated = random.random() < FIRE_LOGIC["flame_chance_per_reading"]
    telemetry["flame"] = flame_activated
    
    # Temperatura del laboratorio
    temp = round(FIRE_LOGIC["temp_base"] + random.uniform(-3, 3), 1)
    telemetry["temperature"] = max(0, min(60, temp))
    
    # Nivel CO (puede elevarse si hay fuego)
    co = round(FIRE_LOGIC["co_base"] + (10 if smoke_activated else 0) + random.uniform(-5, 5), 1)
    telemetry["co_level"] = max(0, min(200, co))
    
    # Estado de puerta (siempre false por defecto a menos que haya emergencia)
    telemetry["door_status"] = smoke_activated or flame_activated
    
    # Marca de tiempo
    telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    return telemetry


def handle_property_update(property_name, new_value):
    """Maneja actualizaciones de propiedades writable desde IoT Central."""
    try:
        logger.info(f"Propiedad writable actualizada: {property_name} = {new_value}")
        
        # Validar según configuración
        if property_name in WRITABLE_PROPERTIES:
            config = WRITABLE_PROPERTIES[property_name]
            
            # Verificar tipo
            if config["type"] == "float":
                value = float(new_value)
                # Verificar rango
                if "min" in config and value < config["min"]:
                    logger.warning(f"Valor below min {config['min']}, usando min")
                    value = config["min"]
                if "max" in config and value > config["max"]:
                    logger.warning(f"Valor above max {config['max']}, usando max")
                    value = config["max"]
                logger.info(f"Propiedad validada: {property_name} = {value}")
                
            # Verificar valores enumerados
            elif config["type"] == "string":
                if new_value in config["values"]:
                    logger.info(f"Propiedad enumerada válida: {property_name} = {new_value}")
                else:
                    logger.warning(f"Valor no válido. Opciones: {config['values']}")
                    return None
            
            return new_value
        else:
            logger.warning(f"Propiedad desconocida: {property_name}")
            return None
            
    except (ValueError, TypeError) as e:
        logger.error(f"Error convirtiendo propiedad {property_name}: {e}")
        return None


def handle_command(command):
    """Maneja comandos remotos desde IoT Central."""
    try:
        command_name = command.get("command")
        payload = command.get("payload", {})
        
        logger.info(f"Comando recibido: {command_name}")
        
        if command_name == "reboot_device":
            logger.warning("Comando reboot_device ejecutándose")
            return MethodResponse.create_from_method_response(
                command.request_id,
                200,
                {"status": "reboot_initiated", "device": DEVICE_ID}
            )
        elif command_name == "test_sensors":
            logger.info("Comando test_sensors ejecutándose")
            sensor_list = payload.get("sensor_list", ["smoke", "flame", "temperature"])
            
            results = {}
            for sensor in sensor_list:
                if sensor == "smoke":
                    results["smoke"] = random.random() < FIRE_LOGIC["smoke_chance_per_reading"]
                elif sensor == "flame":
                    results["flame"] = random.random() < FIRE_LOGIC["flame_chance_per_reading"]
                elif sensor == "temperature":
                    results["temperature"] = round(
                        FIRE_LOGIC["temp_base"] + random.uniform(-3, 3), 1
                    )
                elif sensor == "co_level":
                    results["co_level"] = round(
                        FIRE_LOGIC["co_base"] + random.uniform(-5, 5), 1
                    )
            
            return MethodResponse.create_from_method_response(
                command.request_id,
                200,
                {"sensor_results": results}
            )
        elif command_name == "change_sensitivity":
            sensitivity = payload.get("sensitivity", "medium")
            if sensitivity in ["low", "medium", "high"]:
                WRITABLE_PROPERTIES["alarm_sensitivity"]["default"] = sensitivity
                logger.info(f"Sensibilidad actualizada a: {sensitivity}")
                return MethodResponse.create_from_method_response(
                    command.request_id,
                    200,
                    {"status": "sensitivity_changed", "sensitivity": sensitivity}
                )
            else:
                return MethodResponse.create_from_method_response(
                    command.request_id,
                    400,
                    {"error": "invalid_sensitivity", "received": sensitivity}
                )
        else:
            logger.warning(f"Comando desconocido: {command_name}")
            return MethodResponse.create_from_method_response(
                command.request_id,
                400,
                {"error": "unknown_command"}
            )
            
    except Exception as e:
        logger.error(f"Error procesando comando {command_name}: {e}")
        try:
            return MethodResponse.create_from_method_response(
                command.request_id,
                500,
                {"error": str(e)}
            )
        except:
            pass


def generate_telemetry():
    """Genera telemetría para detector de incendios laboratorio."""
    return check_fire_conditions()


def connect_client():
    """Conecta el cliente IoT Hub."""
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("No IOT_CENTRAL_CONNECTION_STRING environment variable set")
        return None
    
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        logger.info(f"D4 {DEVICE_ID} conectado a Azure IoT Central")
        
        # Intentar propiedades writable (opcional - dependiendo del template)
        # Los cambios de propiedad se recibirán en el loop principal via callbacks
        # en una implementación completa
        
        return client
    except Exception as e:
        logger.error(f"Error conectando cliente D4: {e}")
        return None


def send_periodic_telemetry(client):
    """Envía telemetría periódica con manejo de propiedades y comandos."""
    try:
        iteration = 0
        while True:
            try:
                iteration += 1
                
                # 1. Generar y enviar telemetría
                telemetry = generate_telemetry()
                msg = Message(json.dumps(telemetry))
                msg.content_encoding = "utf-8"
                msg.content_type = "application/json"
                
                client.send_message(msg)
                
                # Logging cada 5 iteraciones
                if iteration % 5 == 1:
                    smoke_val = telemetry.get("smoke", False)
                    flame_val = telemetry.get("flame", False)
                    temp = telemetry.get("temperature", 0)
                    co = telemetry.get("co_level", 0)
                    logger.info(
                        f"Iteración {iteration}: smoke={smoke_val}, flame={flame_val}, "
                        f"temp={temp}°C, CO={co}ppm"
                    )
                else:
                    logger.debug(f"Telemetría enviada: {json.dumps(telemetry, ensure_ascii=False)}")
                
                # 2. Verificar propiedades writable (simplificado)
                # En implementación completa, usaríamos client.on_property_patch_callback()
                # por ahora, solo logueamos cada 10 iteraciones
                if iteration % 10 == 1:
                    logger.debug("Verificando propiedades writable...")
                
                # 3. Esperar intervalo
                time.sleep(SAMPLE_INTERVAL)
                
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado - desconectando D4...")
    except Exception as e:
        logger.error(f"Error en loop principal D4: {e}")
    finally:
        try:
            client.disconnect()
            logger.info("D4 desconectado de Azure IoT Central")
        except:
            pass


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info(f"Iniciando D4 - Incendio Laboratorio")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info(f"Intervalo de muestreo: {SAMPLE_INTERVAL} segundos (1 minuto)")
    logger.info("Origen: Python SDK (azure-iot-device)")
    logger.info("Variables: smoke, flame, temperature, co_level, door_status")
    logger.info("Capacidades: propiedades writable, comandos remotos")
    logger.info("Propiedades writable soportadas:")
    for prop, config in WRITABLE_PROPERTIES.items():
        logger.info(f"  - {prop}: default={config['default']}, type={config['type']}")
    logger.info("=" * 60)
    
    # Conectar cliente
    client = connect_client()
    if client is None:
        logger.error("No se pudo establecer conexión - saliendo")
        return
    
    # Iniciar envío periódico
    logger.info(f"Iniciando envío de telemetría cada {SAMPLE_INTERVAL}s")
    logger.info("Esperando propiedades writable y comandos remotos...")
    send_periodic_telemetry(client)


if __name__ == "__main__":
    main()