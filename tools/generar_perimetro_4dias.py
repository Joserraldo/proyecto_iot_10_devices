#!/usr/bin/env python3
"""
Genera data/perimetro_norte_4dias.csv — dataset de 4 dias NO consecutivos
para D8 (Cerramiento norte). Reproducible con seed fija.

Variables: motion (0/1), lux_nocturno (lux, alto de noche por alumbrado
perimetral), temperature (°C, ciclo diurno nocturno).

Uso: python tools/generar_perimetro_4dias.py [OUTPUT.csv]
"""

import csv
import math
import random
from datetime import datetime, timezone, timedelta
import os

DAYS = [
    datetime(2026, 9, 12, tzinfo=timezone.utc),  # sabado (mas movimiento)
    datetime(2026, 9, 15, tzinfo=timezone.utc),  # martes
    datetime(2026, 9, 19, tzinfo=timezone.utc),  # sabado
    datetime(2026, 9, 22, tzinfo=timezone.utc),  # lunes
]


def gen_day(day, rng):
    rows = []
    for k in range(1440):  # 60s -> 24h
        ts = day + timedelta(minutes=k)
        hour = k / 60.0
        # temperatura: minimo ~03:00 (14C), maximo ~15:00 (27C)
        temp = 20.5 + 6.2 * math.sin(math.radians(hour * 15 - 90 + 15)) + rng.gauss(0, 0.6)
        temp = round(max(14.0, min(28.5, temp)), 1)
        # lux nocturno: alumbrado perimetral 25-48 de 18:00 a 06:00, ~2-8 de dia
        night = (hour < 6.0) or (hour >= 18.0)
        lux = (rng.uniform(25, 48) if night else rng.uniform(2, 8)) + rng.gauss(0, 1.5)
        lux = round(max(0.0, lux), 1)
        # motion: mas eventos de noche y al atardecer
        hour_prob = 0.10 + (0.20 if night else 0.04)
        if 18.0 <= hour < 22.0:
            hour_prob += 0.12
        motion = 1 if rng.random() < hour_prob else 0
        rows.append([ts.isoformat().replace("+00:00", "Z"), str(motion), str(lux), str(temp)])
    return rows


def main():
    out = os.path.join(os.path.dirname(__file__), "..", "data", "perimetro_norte_4dias.csv")
    days = DAYS
    rng = random.Random(20260912)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "motion", "lux_nocturno", "temperature"])
        total = 0
        for d in days:
            w.writerows(gen_day(d, rng))
            total += 1440
    print(f"OK datos/perimetro_norte_4dias.csv: {total} filas en {len(days)} dias no consecutivos")
    for d in days:
        print("  ", d.date())


if __name__ == "__main__":
    main()