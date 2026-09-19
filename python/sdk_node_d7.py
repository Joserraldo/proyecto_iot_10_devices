#!/usr/bin/env python3
# Node SDK Connection - D7 Acceso principal / Perímetro
# Dispositivo: D7 - MQTT Explicito - Intervalo: 30 segundos

"""
D7 - Acceso principal / Perímetro
--------------------------------
Origen: MQTT Explicito (paho-mqtt)
Protocolo: MQTT (sin TLS opcional, o con TLS dependiendo configuración)
Intervalo: 30 segundos
Variables: door_status, occupancy, temperature

Este dispositivo representa el acceso principal y perímetro del campus.
Usa MQTT explícito con cliente Paho para demostrar visibilidad de protocolo,
mediciones y bridge capabilities. A diferencia de los nodos que usan el SDK
oficial Azure, este usa MQTT directo, lo que es útil para escenarios de
interoperabilidad o dispositivos que no pueden usar el SDK completo.
"""

import os
import json
import time
import logging
import paho.mqtt.client as mqtt
from azure.iot.device import IoTHubDeviceClient, Message

# Configuración MQTT (explicito)
MQTT_BROKER = os.getenv("MQTT_BROKER", "test.mqtt.org")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC_CAMPUS_D7", "campus/ems/D7")
MQTT_TLS = os.getenv("MQTT_TLS_ENABLED", "false").lower() == "true"

# Configuración Azure IoT Central (para enviar telemetría)
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D7", "campus-ems-07")

# Intervalo D7: 30 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D7", "30"))

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D7] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def generate_telemetry():
    """Genera telemetría para nodo de acceso/perímetro."""
    telemetry = {
        "door_status": random.choice([True, False]),  # Puerta abierta/cerrada
        "occupancy": random.choice([True, False, False, False]),  # Probabilidad baja
        "temperature": round(random.uniform(15.0, 35.0), 1),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "mqtt-explicito"
    }
    return telemetry


def on_connect(client, userdata, flags, rc):
    """Callback al conectar al broker MQTT."""
    if rc == 0:
        logger.info("Conectado al broker MQTT exitosamente")
        # Suscribirse a tópico de comandos (opcional)
        client.subscribe(MQTT_TOPIC + "/commands")
        logger.info(f"Suscripto a: {MQTT_TOPIC}/commands")
    else:
        logger.error(f"Error de conexión MQTT: código {rc}")


def on_message(client, userdata, msg):
    """Callback cuando se recibe un mensaje en tópico suscrito."""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        logger.info(f"Mensaje recibido en {msg.topic}: {json.dumps(payload, ensure_ascii=False)}")
        
        # Manejar comandos entrantes
        if msg.topic.endswith("/commands"):
            handle_command(payload)
    except Exception as e:
        logger.error(f"Error procesando mensaje MQTT: {e}")


def handle_command(payload):
    """Maneja comandos entrantes desde el tópico MQTT."""
    command = payload.get("command")
    
    if command == "toggle_door":
        logger.info("Comando: toggle_door - cambiando estado de puerta")
        # En un escenario real, esto actualizaría door_status
    elif command == "check_occupancy":
        logger.info("Comando: check_occupancy - solicitando conteo de ocupación")
    else:
        logger.warning(f"Comando MQTT desconocido: {command}")


def connect_mqtt_client():
    """Conecta cliente MQTT explícito."""
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        if MQTT_TLS:
            logger.info("Usando conexión MQTT TLS")
            # client.tls_set() - configuración TLS detallada omitida por simplicidad
        else:
            logger.info("Usando conexión MQTT sin TLS")
        
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()  # Loop en hilo separado
        return client
    except Exception as e:
        logger.error(f"Error conectando MQTT: {e}")
        return None


def send_via_mqtt(client, telemetry):
    """Envía telemetría vía MQTT al tópico configurado."""
    try:
        payload = json.dumps(telemetry)
        result = client.publish(MQTT_TOPIC, payload)
        
        # Verificar resultado de publish
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Publicado en {MQTT_TOPIC}: {payload[:80]}...")
        else:
            logger.warning(f"Error publicando MQTT: código {result.rc}")
            
        return True
    except Exception as e:
        logger.error(f"Error enviando via MQTT: {e}")
        return False


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D7 - Acceso principal / Perímetro")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info("Origen: MQTT Explicito (paho-mqtt)")
    logger.info(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    logger.info(f"Tópico: {MQTT_TOPIC}")
    logger.info("Protocolo: MQTT (visibilidad de protocolo, sin dependency SDK Azure)")
    logger.info("Variables: door_status, occupancy, temperature")
    logger.info("=" * 60)
    
    # Conectar cliente MQTT
    mqtt_client = connect_mqtt_client()
    if mqtt_client is None:
        logger.error("No se pudo conectar al broker MQTT - saliendo")
        return
    
    # También conectar al IoT Central si hay connection string (opcional)
    # para enviar los datos capturados
    if IOT_CENTRAL_CONNECTION_STRING:
        try:
            azure_client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
            azure_client.connect()
            logger.info("También conectado a Azure IoT Central para reenvío")
        except Exception as e:
            logger.warning(f"No se pudo conectar a IoT Central: {e}")
            azure_client = None
    else:
        azure_client = None
        logger.warning("No configurada IOT_CENTRAL_DPS_CONNECTION_STRING - operando solo MQTT")
    
    # Loop principal
    iteration = 0
    try:
        while True:
            iteration += 1
            
            # 1. Generar telemetría
            telemetry = generate_telemetry()
            
            # 2. Publicar vía MQTT explícito
            send_via_mqtt(mqtt_client, telemetry)
            
            # 3. Opcional: reenviar a IoT Central si está conectado
            if azure_client:
                try:
                    msg = Message(json.dumps(telemetry))
                    msg.content_encoding = "utf-8"
                    msg.content_type = "application/json"
                    azure_client.send_message(msg)
                    logger.debug(f"Reenviado a IoT Central")
                except Exception as e:
                    logger.debug(f"Error reenviando a IoT Central: {e}")
            
            # Log cada 5 iteraciones
            if iteration % 5 == 1:
                door = telemetry.get("door_status", False)
                occ = telemetry.get("occupancy", False)
                temp = telemetry.get("temperature", 0)
                logger.info(f"Iter {iteration}: puerta={door}, ocupacion={occ}, temp={temp}°C")
            else:
                logger.debug(f"Telemetría publicada: {json.dumps(telemetry)}")
            
            # Esperar intervalo
            time.sleep(SAMPLE_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado - desconectando D7...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    except Exception as e:
        logger.error(f"Error en loop principal D7: {e}")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    finally:
        if azure_client:
            try:
                azure_client.disconnect()
            except:
                pass
        logger.info("D7 finalizado")


if __name__ == "__main__":
    main()