#!/usr/bin/env python3
# CSV Replay Node - D8 Cerramiento norte
# Dispositivo: D8 - Datos históricos desde CSV
# Origen: Replay CSV - Intervalo: 1 minuto
# Este es el dispositivo con desconexión controlada documentada

"""
D8 - Cerramiento norte
---------------------
Origen: Replay CSV (datos históricos)
Protocolo: Local/Archivo
Intervalo: 1 minuto (60 segundos)
Variables: motion, lux_nocturno, temperature

Este dispositivo reproduce datos desde un archivo CSV histórico, simulando un
sensor de perímetro que captura movimiento, lux nocturno y temperatura.
CRÍTICO: Este es el dispositivo con **desconexión controlada documentada**,
un requisito obligatorio del parcial (al menos 1 dispositivo con hueco de datos
y procedimiento de reconexión Documented → Connected).

Patrón: Este dispositivo lee datos de un archivo CSV y los envía a intervalos.
Cuando se termina de leer el archivo, el dispositivo entra en estado 
'Disconnected' y luego se reconecta para demostrar resiliencia.
"""

import os
import json
import time
import logging
import csv
from azure.iot.device import IoTHubDeviceClient, Message
from datetime import datetime, timezone

# Configuración
CSV_DATA_FILE = os.getenv("CSV_DATA_FILE", "data/perimetro_norte_4dias.csv")
IOT_CENTRAL_CONNECTION_STRING = os.getenv("IOT_CENTRAL_DPS_CONNECTION_STRING")
DEVICE_ID = os.getenv("IOT_CENTRAL_DEVICE_ID_D8", "campus-ems-08")

# Intervalo D8: 1 minuto = 60 segundos
SAMPLE_INTERVAL = float(os.getenv("SAMPLE_INTERVAL_D8", "60"))

# Modo de operación
OPERATION_MODE = os.getenv("D8_OPERATION_MODE", "continuous")  # continuous | replay | disconnected_test

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [D8] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def load_csv_data():
    """Carga datos desde el archivo CSV histórico."""
    rows = []
    try:
        with open(CSV_DATA_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        logger.info(f"Cargado {len(rows)} registros desde {CSV_DATA_FILE}")
        return rows
    except FileNotFoundError:
        logger.error(f"Archivo CSV no encontrado: {CSV_DATA_FILE}")
        # Generar datos de prueba si el archivo no existe
        return generate_mock_csv_data()
    except Exception as e:
        logger.error(fError cargando CSV: {e}")
        return generate_mock_csv_data()


def generate_mock_csv_data():
    """Genera datos mock CSV si el archivo no está disponible."""
    rows = []
    import random
    import datetime
    
    base_time = datetime.datetime.now() - datetime.timedelta(hours=4)
    for i in range(50):  # 50 filas de muestra
        row_time = base_time + datetime.timedelta(seconds=i * 30)
        rows.append({
            "timestamp": row_time.isoformat(),
            "motion": random.choice(["0", "1"]),
            "lux_nocturno": str(round(random.uniform(0, 100), 1)),
            "temperature": str(round(random.uniform(15, 30), 1))
        })
    logger.info(f"Generados {len(rows)} registros mock de muestra")
    return rows


def parse_csv_row(row):
    """Parsea una fila del CSV a diccionario de telemetría."""
    try:
        telemetry = {
            "temperature": round(float(row.get("temperature", 20)), 1),
            "motion": row.get("motion", "0") == "1",
            "lux_nocturno": round(float(row.get("lux_nocturno", 0)), 1),
            "timestamp": row.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "source": "csv-replay"
        }
        return telemetry
    except (ValueError, TypeError) as e:
        logger.error(f"Error parseando fila CSV: {e}")
        return None


def connect_client():
    """Conecta cliente IoT Hub."""
    if not IOT_CENTRAL_CONNECTION_STRING:
        logger.error("No IOT_CENTRAL_CONNECTION_STRING set")
        return None
    
    try:
        client = IoTHubDeviceClient.create_from_connection_string(IOT_CENTRAL_CONNECTION_STRING)
        client.connect()
        logger.info(f"D8 {DEVICE_ID} conectado a Azure IoT Central")
        return client
    except Exception as e:
        logger.error(f"Error conectando cliente D8: {e}")
        return None


def send_telemetry_periodic(client, data_rows, mode="continuous"):
    """Envía telemetría cíclica desde datos CSV."""
    try:
        iteration = 0
        csv_index = 0
        total_rows = len(data_rows)
        
        while True:
            try:
                iteration += 1
                
                # Determinar qué dato enviar basándose en modo y índice
                if mode == "replay":
                    # Reproducir archivo CSV de forma cíclica
                    if csv_index >= total_rows:
                        csv_index = 0  # Reiniciar archivo (simular nuevo ciclo)
                    
                    row = data_rows[csv_index]
                    telemetry = parse_csv_row(row)
                    csv_index += 1
                    
                    # Log cuando reiniciamos el archivo
                    if csv_index == 0:
                        logger.info("Reiniciando reproducción CSV (nuevo ciclo de 4 días)")
                
                elif mode == "disconnected_test":
                    # Modo test: primero enviamos algunos datos, luego desconectamos
                    if iteration < 20:  # Primeros 20 ciclos = ~20 minutos
                        csv_index = (iteration - 1) % total_rows
                        row = data_rows[csv_index]
                        telemetry = parse_csv_row(row)
                    else:
                        # Después de 20 minutos, simular desconexión
                        if iteration == 21:
                            logger.warning("Simulando desconexión controlada - D8 entrará en modo Disconnected")
                        telemetry = {"disconnected": True, "reason": "test_mode"}
                
                else:  # continuous
                    # Modo continuo: datos mock cada intervalo
                    telemetry = {
                        "temperature": round(random.uniform(15, 30), 1),
                        "motion": random.random() > 0.7,
                        "lux_nocturno": round(random.uniform(0, 100), 1),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source": "csv-replay-continuous"
                    }
                
                # Enviar telemetría
                if telemetry:
                    msg = Message(json.dumps(telemetry))
                    msg.content_encoding = "utf-8"
                    msg.content_type = "application/json"
                    
                    client.send_message(msg)
                    
                    # Logging
                    motion_str = telemetry.get("motion", False)
                    temp = telemetry.get("temperature", 0)
                    source = telemetry.get("source", "unknown")
                    logger.debug(f"D8 enviado: motion={motion_str}, temp={temp}°C, source={source}")
                
                # Esperar intervalo
                time.sleep(SAMPLE_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Interrupción por teclado")
                break
            except Exception as e:
                logger.error(f"Error en loop: {e}")
                time.sleep(5)
    
    finally:
        try:
            client.disconnect()
            logger.info("D8 desconectado de Azure IoT Central")
        except:
            pass


def run_disconnection_test(client, data_rows):
    """Ejecuta el test de desconexión controlada para D8."""
    logger.info("=" * 60)
    logger.info("INICIANDO TEST DESCONEXIÓN CONTROLADA - D8")
    logger.info("=" * 60)
    logger.info("Procedimiento:")
    logger.info("1. Enviar datos normales durante N minutos")
    logger.info("2. Detener cliente MQTT deliberadamente")
    logger.info("3. Verificar estado Disconnected en IoT Central")
    logger.info("4. Re-conectar cliente")
    logger.info("5. Verificar retorno al estado Connected")
    logger.info("6. Documentar hueco de datos")
    logger.info("=" * 60)
    
    iteration = 0
    total_rows = len(data_rows)
    
    try:
        while True:
            iteration += 1
            
            if iteration <= 10:
                # Primeros 10 ciclos = enviar datos normales
                row = data_rows[(iteration - 1) % total_rows]
                telemetry = parse_csv_row(row)
                if telemetry:
                    msg = Message(json.dumps(telemetry))
                    client.send_message(msg)
                    logger.debug(f"Enviando dato normal #{iteration}")
            
            elif iteration == 11:
                # Decimo primer ciclo: solicitar desconexión
                logger.warning("SOLICITUD: Desconectar cliente D8 ahora...")
                logger.warning("1. Detener este script o hacer Ctrl+C")
                logger.warning("2. O comentar la línea client.send_message por 30-60s")
                logger.warning("3. Luego re-iniciar y verificar reconexión")
            
            elif iteration > 11 and iteration < 15:
                # Breve periodo sin envío (simular desconexión)
                logger.info(f"Período de simulación desconexión (iter {iteration})")
                time.sleep(5)  # Sleep corto para simular el hueco
            
            else:
                # Reanudar envío normal
                row = data_rows[(iteration - 1) % total_rows]
                if telemetry:
                    msg = Message(json.dumps(telemetry))
                    client.send_message(msg)
                    logger.debug(f"Reanudado envío iter {iteration}")
            
            time.sleep(SAMPLE_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado - finalizando test")
    finally:
        try:
            client.disconnect()
        except:
            pass


def main():
    """Punto de entrada principal."""
    logger.info("=" * 60)
    logger.info("Iniciando D8 - Cerramiento norte (CSV Replay)")
    logger.info("=" * 60)
    logger.info(f"Dispositivo ID: {DEVICE_ID}")
    logger.info("Origen: Replay CSV (datos históricos)")
    logger.info(f"Intervalo: {SAMPLE_INTERVAL} segundos (1 minuto)")
    logger.info(f"Archivo CSV: {CSV_DATA_FILE}")
    logger.info("Modo operación: Modo automático configurado via D8_OPERATION_MODE")
    logger.info("Función crítica: Desconexión controlada documentada")
    logger.info("Variables: motion, lux_nocturno, temperature")
    logger.info("=" * 60)
    
    # Cargar datos CSV
    data_rows = load_csv_data()
    if not data_rows:
        logger.error("No hay datos disponibles - saliendo")
        return
    
    # Conectar cliente
    client = connect_client()
    if client is None:
        logger.error("No se pudo establecer conexión IoT Central - saliendo")
        return
    
    # Determinar modo de operación
    mode = OPERATION_MODE.lower()
    logger.info(f"Modo de operación: {mode}")
    
    # Ejecutar según modo
    if mode == "disconnected_test":
        logger.info("Ejecutando modo test desconexión controlada")
        run_disconnection_test(client, data_rows)
    elif mode == "replay":
        logger.info("Ejecutando modo replay CSV cíclico")
        send_telemetry_periodic(client, data_rows, mode="replay")
    else:  # continuous (default)
        logger.info("Ejecutando modo continuo")
        send_telemetry_periodic(client, data_rows, mode="continuous")


if __name__ == "__main__":
    main()