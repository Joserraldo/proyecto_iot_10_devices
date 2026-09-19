#!/usr/bin/env python3
"""
Simulador local de dispositivo IoT - PARA PRUEBAS SON CREDENCIALES AZURE.
Genera telemetria JSON en consola con asincronia configurable.
Corre sin conexion a Azure: util para verificar que el codigo funciona.

Uso:
  python device_simulator_local.py --type estacion_meteo --interval 15
  python device_simulator_local.py --type incendio --interval 60
  python device_simulator_local.py --type acceso --interval 30
  python device_simulator_local.py --type csv_replay --interval 60 --csv data/perimetro_norte_4dias.csv
"""

import os
import sys
import json
import time
import random
import argparse
import logging
import csv
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIM] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

DEVICE_TYPES = ["estacion_meteo", "patio", "incendio", "calidad_aire",
                "acceso", "csv_replay", "evacuacion", "puesto_mando"]


def estacion_meteo():
    temp = round(25.0 + random.uniform(-5, 5), 1)
    return {
        "temperature": temp,
        "humidity": round(max(20, min(80, 60 - (temp - 20) * 0.5 + random.uniform(-10, 10))), 1),
        "pressure": round(1013.25 + random.uniform(-5, 5), 1),
        "wind_speed": round(random.uniform(0, 15), 1),
        "wind_direction": round(random.uniform(0, 360), 1),
        "rainfall": round(random.uniform(0, 5), 1) if random.random() > 0.7 else 0.0,
    }


def patio():
    return {
        "temperature": round(25.0 + random.uniform(-3, 3), 1),
        "humidity": round(random.uniform(30, 70), 1),
        "lux": round(random.uniform(0, 100000), 1),
    }


def incendio():
    smoke = random.random() < 0.02
    flame = random.random() < 0.005
    return {
        "smoke": smoke,
        "flame": flame,
        "temperature": round(22.0 + random.uniform(-3, 3) + (10 if smoke else 0), 1),
        "co_level": round(25.0 + (10 if smoke else 0) + random.uniform(-5, 5), 1),
        "door_status": smoke or flame,
    }


def calidad_aire():
    return {
        "co2": random.randint(400, 2000),
        "pm25": round(random.uniform(0, 50), 1),
        "pm10": round(random.uniform(0, 100), 1),
        "temperature": round(random.uniform(15, 30), 1),
        "aqi": random.randint(20, 100),
    }


def acceso():
    return {
        "door_status": random.random() > 0.5,
        "occupancy": random.random() > 0.7,
        "temperature": round(random.uniform(15, 35), 1),
    }


def evacuacion():
    return {
        "occupancy": random.choices([0, 1, 2], weights=[0.7, 0.25, 0.05])[0],
        "lux_emergency": round(random.uniform(0, 200), 1),
        "temperature": round(random.uniform(18, 28), 1),
        "emergency_status": "active" if random.random() < 0.05 else "normal",
    }


def puesto_mando():
    connected = random.randint(8, 10)
    return {
        "estado_agregado": {
            "total_devices": 10,
            "connected_devices": connected,
            "disconnected_devices": 10 - connected,
        },
        "temperatura_promedio": round(25.0 + random.uniform(-2, 2), 1),
        "confirmacion_ack": random.choice(["all_clear", "active_alert", "minor_issues"]),
    }


def disconnection_function(value):
    return value


def csv_replay(csv_path):
    """Lee una fila del CSV (ciclico). Si no existe el archivo, genera mock."""
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("timestamp", "").strip() and not row.get("timestamp", "").startswith("<!--"):
                    rows.append(row)
    except FileNotFoundError:
        pass

    if not rows:
        base = datetime.now(timezone.utc) - datetime.timedelta(hours=1)
        for i in range(30):
            rows.append({
                "timestamp": (base + datetime.timedelta(seconds=i * 60)).isoformat(),
                "motion": "1" if random.random() > 0.7 else "0",
                "lux_nocturno": str(round(random.uniform(30, 45), 1)),
                "temperature": str(round(random.uniform(18, 22), 1)),
            })

    if not hasattr(csv_replay, "_idx"):
        csv_replay._idx = 0
    row = rows[csv_replay._idx % len(rows)]
    csv_replay._idx += 1
    return {
        "motion": row["motion"] == "1",
        "lux_nocturno": round(float(row["lux_nocturno"]), 1),
        "temperature": round(float(row["temperature"]), 1),
        "source": "csv-replay",
        "row_index": csv_replay._idx,
    }


GENERATORS = {
    "estacion_meteo": estacion_meteo,
    "patio": patio,
    "incendio": incendio,
    "calidad_aire": calidad_aire,
    "acceso": acceso,
    "evacuacion": evacuacion,
    "puesto_mando": puesto_mando,
}


def run(type_name, interval, iterations, disconnect_at, csv_path):
    gen = GENERATORS.get(type_name)
    if type_name == "csv_replay":
        gen = lambda: csv_replay(csv_path)

    logger.info("=" * 50)
    logger.info(f"Simulador local iniciado - tipo: {type_name}")
    logger.info(f"Intervalo: {interval}s | Iteraciones: {iterations or 'infinitas'}")
    if disconnect_at:
        logger.info(f"Desconexion simulada en la iteracion: {disconnect_at}")
    logger.info("=" * 50)

    telemetry = None
    i = 0
    try:
        while iterations is None or i < iterations:
            i += 1

            if disconnect_at and i == disconnect_at:
                logger.warning(f"[Iter {i}] >>> DESCONEXION CONTROLADA: deteniendo envio...")
                time.sleep(interval)
                logger.info(f"[Iter {i}] >>> RECONEXION: reanudando envio...")
                continue

            telemetry = gen()
            telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()
            telemetry["device_id"] = f"campus-ems-{type_name}"
            telemetry["interval"] = interval
            print(json.dumps(telemetry, ensure_ascii=False))
            logger.info(f"[Iter {i}] Telemetria enviada")

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Detenido por el usuario (Ctrl+C)")
    logger.info("Simulacion finalizada")


def main():
    parser = argparse.ArgumentParser(description="Simulador local de dispositivos IoT (sin Azure)")
    parser.add_argument("--type", choices=DEVICE_TYPES, default="estacion_meteo",
                        help="Tipo de dispositivo a simular")
    parser.add_argument("--interval", type=float, default=15.0,
                        help="Intervalo de muestreo en segundos")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Numero maximo de iteraciones (por defecto infinito)")
    parser.add_argument("--disconnect-at", type=int, default=None,
                        help="Iteracion en la que simular desconexion controlada")
    parser.add_argument("--csv", default="data/perimetro_norte_4dias.csv",
                        help="Ruta del CSV para modo csv_replay")
    args = parser.parse_args()

    run(args.type, args.interval, args.iterations, args.disconnect_at, args.csv)


if __name__ == "__main__":
    main()