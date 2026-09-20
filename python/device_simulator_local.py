#!/usr/bin/env python3
"""
Simulador local de dispositivo IoT — SIN credenciales Azure.
Genera telemetría JSON en consola con asincronía configurable.
Útil para verificar lógica de generación de datos sin conectar a la nube.

Uso:
  python device_simulator_local.py --type estacion_meteo --interval 15
  python device_simulator_local.py --type incendio --interval 60
  python device_simulator_local.py --type acceso --interval 30
  python device_simulator_local.py --type csv_replay --interval 60
  python device_simulator_local.py --type incendio --disconnect-at 5 --iterations 10
"""

import os
import json
import time
import random
import argparse
import logging
import csv
from datetime import datetime, timezone, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [SIM] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEVICE_TYPES = [
    "estacion_meteo", "patio", "incendio", "calidad_aire",
    "acceso", "csv_replay", "evacuacion", "puesto_mando",
]


# -------------------------------------------------------------------
# Generadores de telemetría por tipo
# -------------------------------------------------------------------

def estacion_meteo():
    temp = round(25.0 + random.uniform(-5, 5), 1)
    return {
        "temperature": temp,
        "humidity": round(max(20.0, min(80.0, 60.0 - (temp - 20) * 0.5 + random.uniform(-10, 10))), 1),
        "pressure": round(1013.25 + random.uniform(-5, 5), 1),
        "wind_speed": round(random.uniform(0, 15), 1),
        "wind_direction": round(random.uniform(0, 360), 1),
        "rainfall": round(random.uniform(0, 5), 1) if random.random() > 0.7 else 0.0,
    }


def patio():
    return {
        "temperature": round(25.0 + random.uniform(-3, 3), 1),
        "humidity": round(random.uniform(30, 70), 1),
        "lux": round(random.uniform(0, 100_000), 1),
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
        "co2_sim": random.randint(400, 2000),
        "pm25_sim": round(random.uniform(0, 50), 1),
        "pm10_sim": round(random.uniform(0, 100), 1),
        "temperature": round(random.uniform(15, 30), 1),
        "aqi": random.randint(20, 100),
    }


def acceso():
    return {
        "door_status": random.random() > 0.6,
        "occupancy": random.random() > 0.75,
        "temperature": round(random.uniform(15, 35), 1),
    }


def evacuacion():
    return {
        "occupancy": random.choices([0, 1, 2], weights=[0.70, 0.25, 0.05], k=1)[0],
        "lux_emergency": round(random.uniform(0, 200), 1),
        "temperature": round(random.uniform(18, 28), 1),
        "emergency_status": "active" if random.random() < 0.05 else "normal",
    }


def puesto_mando():
    connected = random.randint(8, 10)
    ack_status = random.choice(["all_clear", "active_alert", "minor_issues"])
    return {
        "connected_devices": connected,
        "disconnected_devices": 10 - connected,
        "system_health": round(random.uniform(85, 100), 1),
        "temperatura_promedio": round(25.0 + random.uniform(-2, 2), 1),
        "ack_pending": 0 if ack_status == "all_clear" else random.randint(1, 3),
        "ack_status": ack_status,
        "system_uptime": round(random.uniform(95, 100), 1),
    }


_csv_idx = 0


def csv_replay(csv_path):
    """Lee filas del CSV de forma cíclica; genera mock si el archivo no existe."""
    global _csv_idx
    rows = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ts = row.get("timestamp", "").strip()
                if ts and not ts.startswith("<!--") and ts != "...":
                    rows.append(row)
    except FileNotFoundError:
        pass

    if not rows:
        base = datetime.now(timezone.utc) - timedelta(hours=1)
        for i in range(30):
            rows.append({
                "timestamp": (base + timedelta(minutes=i * 2)).isoformat(),
                "motion": "1" if random.random() > 0.7 else "0",
                "lux_nocturno": str(round(random.uniform(30, 45), 1)),
                "temperature": str(round(random.uniform(18, 22), 1)),
            })

    row = rows[_csv_idx % len(rows)]
    _csv_idx += 1
    return {
        "motion": row["motion"] == "1",
        "lux_nocturno": round(float(row["lux_nocturno"]), 1),
        "temperature": round(float(row["temperature"]), 1),
        "source": "csv-replay",
        "row_index": _csv_idx,
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
    if type_name == "csv_replay":
        gen = lambda: csv_replay(csv_path)
    else:
        gen = GENERATORS.get(type_name)
        if gen is None:
            logger.error(f"Tipo desconocido: {type_name}")
            return

    logger.info("=" * 50)
    logger.info(f"[SIM] Tipo: {type_name} | Intervalo: {interval}s | Iter: {iterations or '∞'}")
    if disconnect_at:
        logger.info(f"[SIM] Desconexión simulada en iteración: {disconnect_at}")
    logger.info("=" * 50)

    i = 0
    try:
        while iterations is None or i < iterations:
            i += 1

            if disconnect_at and i == disconnect_at:
                logger.warning(f"[SIM] iter={i} >>> DESCONEXIÓN CONTROLADA: pausa {interval}s...")
                time.sleep(interval)
                logger.info(f"[SIM] iter={i} >>> RECONEXIÓN: reanudando...")
                continue

            telemetry = gen()
            telemetry["timestamp"] = datetime.now(timezone.utc).isoformat()
            telemetry["device_id"] = f"campus-ems-{type_name}"
            telemetry["interval_s"] = interval

            print(json.dumps(telemetry, ensure_ascii=False))
            logger.info(f"[SIM] iter={i} telemetría generada")

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("[SIM] Detenido por usuario (Ctrl+C)")

    logger.info("[SIM] Simulación finalizada")


def main():
    parser = argparse.ArgumentParser(description="Simulador local IoT (sin Azure)")
    parser.add_argument("--type", choices=DEVICE_TYPES, default="estacion_meteo",
                        help="Tipo de dispositivo a simular")
    parser.add_argument("--interval", type=float, default=15.0,
                        help="Intervalo de muestreo en segundos")
    parser.add_argument("--iterations", type=int, default=None,
                        help="Número máximo de iteraciones (por defecto: infinito)")
    parser.add_argument("--disconnect-at", type=int, default=None,
                        help="Iteración en la que simular desconexión controlada")
    parser.add_argument("--csv", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "perimetro_norte_4dias.csv"),
                        help="Ruta del CSV para modo csv_replay")
    args = parser.parse_args()
    run(args.type, args.interval, args.iterations, args.disconnect_at, args.csv)


if __name__ == "__main__":
    main()
