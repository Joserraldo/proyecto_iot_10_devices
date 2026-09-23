#!/usr/bin/env python3
"""
dashboard_server.py — Sala de control Campus EMS (10 dispositivos).

Sirve
-----
  GET  /                     grid de la flota. Un solo request (/api/live) alimenta
                             las 10 tarjetas + KPIs + sparklines.
  GET  /device/{id}          vista detalle del dispositivo (histórico navegable).
  GET  /chart/{id}           vista ampliada de una métrica (zoom/pan tipo IoT Central).
  GET  /evidencias           tablero de evidencias: cobertura, intervalos, stats,
                             desconexiones, logs Wokwi, checks del parcial.
  GET  /api/live             UN request con estado + valores + sparkline de los 10 devices.
  GET  /api/status           alias de compatibilidad (mismo contenido de devices).
  GET  /api/history          histórico. Parámetros:
                               id=01..10
                               range=1h|6h|24h|72h|7d|all   (por defecto 24h)
                               from=<epoch>&to=<epoch>       (ventana explícita)
                               max=N                         (máx puntos devueltos, downsample)
                               raw=1                         (puntos crudos, sin downsample)
                               limit=N                       (compat: límite de puntos crudos)
                             Devuelve además `stats` calculadas sobre TODA la ventana.
  GET  /api/export?id=01&range=all&fmt=csv   descarga CSV del histórico.
  GET  /api/logs?id=01&n=120&src=device|wokwi   últimas líneas de log.
  POST /api/dispatch[?dev=01]                "Llamar asesor" (correo con la ubicación).

Cómo carga los datos
--------------------
El histórico se acumula leyendo incrementalmente (por offset de bytes) los archivos
~/iotlogs/dX.log producidos por los nodos, buscando las líneas ``[DX] TELE {json}``.
Se persiste en ~/iotlogs/history/dX.jsonl para sobrevivir reinicios de la flota.

Rendimiento
-----------
- El escaneo de logs disparado por HTTP está limitado a una vez cada SCAN_MIN_S segundos
  (el hilo de fondo lo hace igual cada 15 s mientras haya alguien mirando el dashboard).
- Las gráficas nunca reciben más de `max` puntos: el servidor hace downsample por
  cubetas conservando mínimos y máximos (no se pierden picos).
- Las estadísticas se calculan sobre la ventana completa, no sobre lo dibujado.

Config (variables de entorno o ../.env):
  BREVO_API_KEY, BREVO_TO_EMAIL, BREVO_SENDER_EMAIL, ADVISOR_PHONE, DASH_PORT,
  LOG_DIR, HISTORY_DIR, REALERT_S, MIN_EXTREME_S, ACTIVE_WINDOW, HIST_MAX, SCAN_MIN_S

Uso:
  python dashboard_server.py             # servidor en 0.0.0.0:8080
  python dashboard_server.py --test-mail # envía 1 mail de prueba y sale
  python dashboard_server.py --selftest  # checks de lógica y sale
"""

import json
import os
import re
import sys
import time
import calendar
import threading
import http.server
from datetime import datetime, timezone
from urllib.parse import unquote_plus

try:
    import requests
except ImportError:
    requests = None

BASE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- config
def _load_env():
    env = {}
    try:
        with open(os.path.join(BASE, "..", ".env"), encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return env


_env = _load_env()
BREVO_API_KEY = os.getenv("BREVO_API_KEY") or _env.get("BREVO_API_KEY", "")
BREVO_TO_EMAIL = os.getenv("BREVO_TO_EMAIL") or _env.get("BREVO_TO_EMAIL", "")
BREVO_SENDER = os.getenv("BREVO_SENDER_EMAIL") or _env.get("BREVO_SENDER_EMAIL") or BREVO_TO_EMAIL
ADVISOR_PHONE = os.getenv("ADVISOR_PHONE") or _env.get("ADVISOR_PHONE", "+573****0000")
LOG_DIR = os.getenv("LOG_DIR") or os.path.expanduser("~/iotlogs")
HISTORY_DIR = os.getenv("HISTORY_DIR") or os.path.join(LOG_DIR, "history")
PORT = int(os.getenv("DASH_PORT", "8080"))
REALERT_S = int(os.getenv("REALERT_S", "86400"))          # re-notificar si sigue extremo (24 h)
MIN_EXTREME_S = int(os.getenv("MIN_EXTREME_S", "300"))    # extremo sostenido antes de alertar (5 min)
ACTIVE_WINDOW = int(os.getenv("ACTIVE_WINDOW", "300"))    # sin requests → pausar scan/alertas (5 min)
HIST_MAX = int(os.getenv("HIST_MAX", "200000"))           # máx puntos por device en memoria
CHART_MAX = int(os.getenv("CHART_MAX", "2000"))           # máx puntos por gráfica
SPARK_N = int(os.getenv("SPARK_N", "72"))                 # puntos por sparkline del grid
SCAN_MIN_S = float(os.getenv("SCAN_MIN_S", "2.0"))        # escaneo mínimo entre requests
WOKWI_LOG = os.getenv("WOKWI_LOG") or os.path.join(LOG_DIR, "wokwi_d2.log")

# metadatos del despliegue (para el tablero de evidencias)
ID_SCOPE = os.getenv("DPS_ID_SCOPE") or _env.get("DPS_ID_SCOPE", "0ne012B4879")
IOT_HUB = os.getenv("IOT_HUB_HOST") or _env.get("IOT_HUB_HOST", "")
DEVICE_TEMPLATE = "campus-emergency-v1 (dtmi:campusems:campusEmergencyV1;1)"

# ---------------------------------------------------------------- catálogo
DEVICES = [
    {"id": "01", "name": "Estación meteo campus", "loc": "Campus", "interval": 15, "origin": "Digital Twin · MQTT/TLS"},
    {"id": "02", "name": "Meteo patio (Wokwi)", "loc": "Patio", "interval": 30, "origin": "Wokwi ESP32 · MQTT"},
    {"id": "03", "name": "Incendio Bloque A", "loc": "Bloque A", "interval": 60, "origin": "Python SDK · MQTT/TLS"},
    {"id": "04", "name": "Incendio Laboratorio", "loc": "Laboratorio", "interval": 60, "origin": "Python SDK · MQTT/TLS"},
    {"id": "05", "name": "Calidad aire aula", "loc": "Aula", "interval": 15, "origin": "API pública · HTTPS"},
    {"id": "06", "name": "Calidad aire exterior", "loc": "Exterior", "interval": 300, "origin": "Atlas/WAQI · HTTPS"},
    {"id": "07", "name": "Acceso principal", "loc": "Puerta principal", "interval": 30, "origin": "MQTT explícito"},
    {"id": "08", "name": "Cerramiento norte", "loc": "Perímetro norte", "interval": 60, "origin": "Replay CSV · local"},
    {"id": "09", "name": "Evacuación pasillo", "loc": "Pasillo", "interval": 45, "origin": "Digital Twin · MQTT/TLS"},
    {"id": "10", "name": "Puesto de mando", "loc": "Centro de mando", "interval": 20, "origin": "Digital Twin · MQTT/TLS"},
]
DEV_BY_ID = {d["id"]: d for d in DEVICES}

# Extremos: (min, max); bounds=None = booleano donde 1/True es extremo.
EXTREMES = {
    "temperature": (None, 70.0), "temperatura_promedio": (None, 70.0),
    "humidity": (5.0, 98.0), "co2_sim": (None, 2500.0), "no2_sim": (None, 800.0),
    "pm25": (None, 700.0), "pm25_sim": (None, 700.0), "pm10_sim": (None, 1200.0),
    "aqi": (None, 400.0), "co_level": (None, 800.0), "wind_speed": (None, 150.0),
    "sound_level": (None, 140.0), "sound_alert": (None, 140.0),
    "smoke": None, "flame": None,
}

UNITS = {
    "temperature": "°C", "humidity": "%", "pressure": "hPa", "wind_speed": "m/s",
    "wind_direction": "°", "rainfall": "mm", "lux": "lux", "lux_nocturno": "lux",
    "lux_emergency": "lux", "pm25": "µg/m³", "pm25_sim": "µg/m³", "pm10_sim": "µg/m³",
    "aqi": "AQI", "co_level": "ppm", "co2_sim": "ppm", "no2_sim": "ppm",
    "temperatura_promedio": "°C", "sound_level": "dB", "sound_alert": "dB",
    "system_health": "%", "system_uptime": "%", "occupancy": "pers",
    "connected_devices": "disp", "disconnected_devices": "disp", "ack_pending": "disp",
}
LABELS = {
    "temperature": "Temp", "humidity": "Humedad", "pressure": "Presión",
    "wind_speed": "Viento", "wind_direction": "Dir viento", "rainfall": "Lluvia",
    "lux": "Luz", "lux_nocturno": "Luz nocturna", "lux_emergency": "Luz emergencia",
    "pm25": "PM2.5", "pm25_sim": "PM2.5", "pm10_sim": "PM10",
    "aqi": "AQI", "co_level": "CO", "co2_sim": "CO2", "no2_sim": "NO2",
    "smoke": "Humo", "flame": "Llama", "motion": "Movimiento", "door_status": "Puerta",
    "occupancy": "Ocupación", "connected_devices": "Conectados", "ack_status": "ACK",
    "emergency_status": "Emergencia", "api_source": "Fuente", "temperatura_promedio": "Temp prom",
    "sound_level": "Ruido", "sound_alert": "Ruido", "source": "Fuente", "device_id": "Device",
    "system_health": "Salud", "system_uptime": "Uptime", "disconnected_devices": "Descon.",
    "ack_pending": "ACK pend.", "mqtt_status": "MQTT", "csv_row": "CSV fila",
}
# campos que no se grafican ni se cuentan como métrica
SKIP_FIELDS = {"timestamp", "api_source", "source", "device_id", "csv_row", "mqtt_status",
               "ack_status", "emergency_status", "door_status", "motion", "ack_pending",
               "_bridge", "_source", "_timestamp"}
# orden preferido para elegir la métrica principal de cada device
MAIN_FIELDS = ["temperature", "temperature_promedio", "pm25", "pm25_sim", "co_level",
               "co2_sim", "aqi", "lux_emergency", "lux", "sound_level", "occupancy",
               "connected_devices", "motion", "smoke", "flame"]

TELE_RE = re.compile(r"\[D(\d{1,2})\] TELE (\{.*\})")

RANGES = {"1h": 3600, "6h": 21600, "24h": 86400, "72h": 259200, "7d": 604800}

# ---------------------------------------------------------------- histórico
_buf = {}        # dev_id -> list of {"t": iso, "ts": float, "v": {...}}
_offsets = {}    # dev_id -> byte offset leído del log
_seen = {}       # dev_id -> set(clave de dedup)
_hist_lock = threading.Lock()
_started_at = time.time()


def _dev_log(dev_id):
    return os.path.join(LOG_DIR, f"d{int(dev_id)}.log")


def _dev_hist(dev_id):
    return os.path.join(HISTORY_DIR, f"d{int(dev_id)}.jsonl")


def _init_history():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    for d in DEVICES:
        did = d["id"]
        _buf[did] = []
        _offsets[did] = 0
        _seen[did] = set()
        try:
            with open(_dev_hist(did), encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        _buf[did].append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        # descarta puntos con timestamp absurdo (p. ej. de un histórico escrito con
        # la zona horaria mal interpretada) para que no oculten datos reales
        limite = time.time() + 86400
        _buf[did] = [p for p in _buf[did] if isinstance(p.get("ts"), (int, float)) and p["ts"] <= limite]
        _buf[did].sort(key=lambda p: p["ts"])
        _seen[did] = {p.get("t") for p in _buf[did]}
        if len(_buf[did]) > HIST_MAX:
            _buf[did] = _buf[did][-HIST_MAX:]


def _persist(dev_id):
    try:
        tmp = _dev_hist(dev_id) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for p in _buf[dev_id]:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        os.replace(tmp, _dev_hist(dev_id))
    except OSError as e:
        print(f"[HIST] {dev_id}: no se pudo persistir: {e}", flush=True)


def _append(dev_id, item):
    buf = _buf[dev_id]
    buf.append(item)
    if len(buf) > HIST_MAX:
        del buf[: len(buf) - HIST_MAX]
        _seen[dev_id] = {p.get("t") for p in buf}
    if len(buf) % 25 == 0:
        _persist(dev_id)


def read_new(dev_id):
    """Lee líneas TELE nuevas del log (incremental por offset)."""
    path = _dev_log(dev_id)
    try:
        size = os.path.getsize(path)
    except OSError:
        return
    off = _offsets.get(dev_id, 0)
    if off > size:                      # log truncado (reinicio de flota)
        off = 0
    with open(path, "rb") as f:
        f.seek(off)
        data = f.read()
        _offsets[dev_id] = f.tell()
    if not data:
        return
    for line in data.decode("utf-8", "replace").splitlines():
        m = TELE_RE.search(line)
        if not m or int(m.group(1)) != int(dev_id):
            continue
        try:
            v = json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        raw = v.pop("timestamp", None)
        key = raw or json.dumps(v, sort_keys=True)
        if key in _seen[dev_id]:
            continue
        _seen[dev_id].add(key)
        ts = None
        if isinstance(raw, str):
            low = raw.replace("Z", "+00:00")
            try:
                # los nodos publican ISO-8601 en UTC → interpretar como UTC
                # (con mktime se asumía hora local y el punto se corría de zona)
                ts = calendar.timegm(time.strptime(low[:19], "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, TypeError):
                ts = None
        now = time.time()
        _append(dev_id, {"t": raw or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                         "ts": ts or now, "v": v})


def read_latest(dev_id):
    buf = _buf.get(dev_id) or []
    return buf[-1]["v"] if buf else None


def _tail_lines(path, n=120, chunk=32768):
    try:
        size = os.path.getsize(path)
    except OSError:
        return []
    if size <= 0:
        return []
    with open(path, "rb") as f:
        f.seek(max(0, size - chunk))
        data = f.read().decode("utf-8", "replace")
    out = [ln.rstrip() for ln in data.splitlines() if ln.strip()]
    return out[-n:]


def _tail_log(dev_id, n=120):
    return _tail_lines(_dev_log(dev_id), n)


def _tail_wokwi(n=120):
    return _tail_lines(WOKWI_LOG, n)


def device_points(dev_id, limit=None, after=None, before=None):
    pts = _buf.get(dev_id) or []
    if after is not None:
        pts = [p for p in pts if p["ts"] >= after]
    if before is not None:
        pts = [p for p in pts if p["ts"] <= before]
    if limit and limit > 0 and len(pts) > limit:
        pts = pts[-limit:]
    return pts


def _online(dev, now):
    try:
        mt = os.path.getmtime(_dev_log(dev["id"]))
    except OSError:
        return False
    return (now - mt) <= max(120, 4 * dev["interval"])


def current_extremes(values):
    out = []
    for field, bounds in EXTREMES.items():
        if field not in values:
            continue
        val = values[field]
        if bounds is None:
            if val in (1, True):
                out.append(field)
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        lo, hi = bounds
        if (lo is not None and num <= lo) or (hi is not None and num >= hi):
            out.append(field)
    return out


# ---------------------------------------------------------------- análisis
def _main_field(values):
    if not values:
        return None
    for f in MAIN_FIELDS:
        if f in values and not isinstance(values[f], bool) and isinstance(values[f], (int, float)):
            return f
    for k, v in values.items():
        if k in SKIP_FIELDS or k not in LABELS:
            continue
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return k
    return None


def downsample_minmax(points, max_pts):
    """Reduce conservando mínimos y máximos por cubeta (no se pierden picos)."""
    n = len(points)
    if max_pts <= 0 or n <= max_pts:
        return points
    out = []
    n_buckets = max(1, max_pts // 2)
    size = n / n_buckets
    for b in range(n_buckets):
        lo_i = int(b * size)
        hi_i = int((b + 1) * size)
        seg = points[lo_i:max(hi_i, lo_i + 1)]
        if not seg:
            continue
        if len(seg) == 1:
            out.append(seg[0])
            continue
        fl = _main_field(seg[-1]["v"])
        numeric = fl and all(isinstance(v.get(fl), (int, float)) and not isinstance(v.get(fl), bool)
                             for v in (p["v"] for p in seg))
        if numeric:
            imin = min(range(len(seg)), key=lambda i: seg[i]["v"][fl])
            imax = max(range(len(seg)), key=lambda i: seg[i]["v"][fl])
            first, second = (imin, imax) if imin <= imax else (imax, imin)
            out.append(seg[first])
            if second != first:
                out.append(seg[second])
        else:
            out.append(seg[len(seg) // 2])
    return out


def window_stats(points, fields=None):
    """Estadísticas sobre TODA la ventana (no sobre lo dibujado)."""
    if not points:
        return {}
    keys = set()
    for p in points:
        keys.update(p["v"].keys())
    if fields:
        keys &= set(fields)
    out = {}
    for k in sorted(keys):
        if k in SKIP_FIELDS:
            continue
        nums, non_num = [], None
        for p in points:
            v = p["v"].get(k)
            if isinstance(v, bool) or v is None:
                continue
            if isinstance(v, (int, float)):
                nums.append(float(v))
            else:
                non_num = v
        if nums:
            out[k] = {
                "count": len(nums), "min": min(nums), "max": max(nums),
                "avg": sum(nums) / len(nums), "sum": sum(nums),
                "last": nums[-1], "unit": UNITS.get(k, ""), "label": LABELS.get(k, k),
            }
        elif non_num is not None:
            out[k] = {"count": len(points), "last": non_num, "label": LABELS.get(k, k), "text": True}
    return out


def detect_gaps(dev, window_s=None):
    """Cortes de telemetría: huecos mayores a 3x el intervalo esperado."""
    pts = _buf.get(dev["id"]) or []
    if window_s:
        cut = time.time() - window_s
        pts = [p for p in pts if p["ts"] >= cut]
    if len(pts) < 2:
        return []
    tol = max(180, dev["interval"] * 3)
    gaps = []
    for a, b in zip(pts, pts[1:]):
        d = b["ts"] - a["ts"]
        if d > tol:
            gaps.append({"from": a["t"], "to": b["t"], "seconds": round(d, 1),
                         "from_ts": a["ts"], "to_ts": b["ts"]})
    return gaps


def _series(dev_id, field, n):
    pts = [p for p in (_buf.get(dev_id) or []) if isinstance(p["v"].get(field), (int, float))]
    if len(pts) > n:
        step = len(pts) / n
        pts = [pts[int(i * step)] for i in range(n)]
    return [p["v"][field] for p in pts]


# ---------------------------------------------------------------- mail
_alerts = {}
_dispatch_stats = {"count": 0, "last_ts": None, "last_dev": None}


def send_brevo(subject, html):
    if not BREVO_API_KEY:
        print(f"[ALERT] BREVO_API_KEY no configurado — saltando correo: {subject}", flush=True)
        return False
    if requests is None:
        print("[ALERT] requests no instalado — no se pudo enviar mail", flush=True)
        return False
    payload = {
        "sender": {"name": "Campus EMS", "email": BREVO_SENDER},
        "to": [{"email": BREVO_TO_EMAIL}],
        "subject": subject,
        "htmlContent": html,
    }
    try:
        r = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": BREVO_API_KEY, "accept": "application/json",
                     "content-type": "application/json"},
            json=payload, timeout=20,
        )
    except Exception as e:
        print(f"[ALERT] Brevo error de red: {e}", flush=True)
        return False
    if r.status_code not in (200, 201):
        print(f"[ALERT] Brevo {r.status_code}: {r.text[:300]}", flush=True)
        return False
    print(f"[ALERT] Mail enviado: {subject}", flush=True)
    return True


def check_and_alert(dev, values, now):
    hits = []
    for field, bounds in EXTREMES.items():
        if field not in values:
            continue
        val = values[field]
        if bounds is None:
            extreme = val in (1, True)
        else:
            try:
                num = float(val)
            except (TypeError, ValueError):
                extreme = False
            else:
                lo, hi = bounds
                extreme = (lo is not None and num <= lo) or (hi is not None and num >= hi)
        key = (dev["id"], field)
        st = _alerts.get(key, {"since": 0.0, "last_sent": 0.0})
        if not extreme:
            st["since"] = 0.0
            _alerts[key] = st
            continue
        if st["since"] == 0.0:
            st["since"] = now
            _alerts[key] = st
            continue
        if (now - st["since"]) < MIN_EXTREME_S:
            _alerts[key] = st
            continue
        if (now - st["last_sent"]) < REALERT_S:
            _alerts[key] = st
            continue
        st["last_sent"] = now
        _alerts[key] = st
        hits.append((field, val))
    if hits:
        detalle = "".join(
            f"<li><b>{LABELS.get(f, f)}</b> = {v} {UNITS.get(f, '')} (device {dev['name']})</li>"
            for f, v in hits
        )
        send_brevo(
            f"Campus EMS — ALERTA extrema en {dev['id']}",
            f"<p>El dispositivo <b>{dev['name']}</b> ({dev['loc']}) excedió el umbral extremo:</p>"
            f"<ul>{detalle}</ul>"
            f"<p>Fecha: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>",
        )


def dispatch_advisor(dev_id=None):
    """'Llamar asesor' → correo de despacho con el lugar al que debe ir el asesor."""
    now = time.time()
    if now - (_dispatch_stats["last_ts"] or 0) < 15:
        return {"ok": True, "throttled": True, "message": "Despacho ya enviado hace instantes."}
    if dev_id:
        devs = [d for d in DEVICES if d["id"] == dev_id]
    else:
        devs = [d for d in DEVICES if current_extremes(read_latest(d["id"]) or {})] or DEVICES
    context = [{"dev": d, "values": read_latest(d["id"]) or {}} for d in devs]
    context = [c for c in context if c["values"]]
    if not context:
        return {"ok": False, "message": "Sin lecturas disponibles para despachar."}
    filas = []
    for c in context[:6]:
        d, vals = c["dev"], c["values"]
        ext = current_extremes(vals)
        motivo = ", ".join(LABELS.get(f, f) for f in ext) if ext else "sin alerta extrema"
        filas.append(
            f"<tr><td><b>{d['id']}</b></td><td>{d['name']}</td>"
            f"<td><b>{d['loc']}</b></td><td>{motivo}</td></tr>"
        )
    if len(context) > 6:
        filas.append(f"<tr><td colspan=4>… y {len(context) - 6} dispositivos más.</td></tr>")
    t = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    html = (
        "<h2>Despacho de asesor — Campus EMS</h2>"
        "<p>Se solicita presencia en terreno. El asesor debe dirigirse a la ubicación "
        "del dispositivo en estado de alerta:</p>"
        "<table border='1' cellpadding='6' cellspacing='0' style='border-collapse:collapse'>"
        "<tr style='background:#efefef'><th>Dev</th><th>Dispositivo</th><th>Ubicación</th><th>Alertas</th></tr>"
        + "".join(filas) +
        "</table>"
        f"<p>Contacto de coordinación: <a href='tel:{ADVISOR_PHONE}'>{ADVISOR_PHONE}</a></p>"
        f"<p>Fecha: {t}</p>"
    )
    ok = send_brevo("Campus EMS — Despacho de asesor: ubicación de la alerta", html)
    if ok:
        _dispatch_stats.update({"count": _dispatch_stats["count"] + 1,
                                "last_ts": now, "last_dev": dev_id or "flota"})
    return {"ok": ok, "throttled": False,
            "message": "Mail de despacho enviado." if ok else "Fallo al enviar mail."}


# ---------------------------------------------------------------- estado
_last_scan = {"ts": 0.0}
_status = {}
_summary = {}
_activity = {"ts": 0.0}
_scan_lock = threading.Lock()


def _touch_activity():
    _activity["ts"] = time.time()


def _recently_active():
    return (time.time() - _activity["ts"]) <= ACTIVE_WINDOW


def build_status(now=None):
    now = now or time.time()
    for dev in DEVICES:
        values = read_latest(dev["id"]) or {}
        pts = _buf.get(dev["id"]) or []
        _status[dev["id"]] = {
            **dev,
            "online": _online(dev, now),
            "values": values,
            "extremes": current_extremes(values),
            "points": len(pts),
            "last_ts": pts[-1]["ts"] if pts else None,
            "main_field": _main_field(values),
        }
        if values:
            check_and_alert(dev, values, now)
    _summary.update(_build_summary(now))
    _last_scan["ts"] = now


def _build_summary(now):
    online = sum(1 for d in DEVICES if _status.get(d["id"], {}).get("online"))
    alerts = [
        {"id": d["id"], "name": d["name"], "loc": d["loc"],
         "extremes": _status[d["id"]].get("extremes", [])}
        for d in DEVICES if _status.get(d["id"], {}).get("extremes")
    ]
    nums = {}
    for d in DEVICES:
        v = _status.get(d["id"], {}).get("values", {})
        for k, x in v.items():
            if k in EXTREMES and isinstance(x, (int, float)) and not isinstance(x, bool):
                nums.setdefault(k, []).append(float(x))
    kpi = {}
    for k, xs in nums.items():
        kpi[k] = {"last": xs[-1], "min": min(xs), "max": max(xs), "avg": sum(xs) / len(xs)}
    return {"total": len(DEVICES), "online": online, "offline": len(DEVICES) - online,
            "alerts": alerts, "kpis": kpi, "ts": now,
            "dispatches": _dispatch_stats["count"]}


def scan_once(force=False):
    """Escanea logs y recalcula estado. Throttled salvo force=True."""
    now = time.time()
    with _scan_lock:
        if not force and _last_scan["ts"] > 0 and (now - _last_scan["ts"]) < SCAN_MIN_S:
            return False
        for dev in DEVICES:
            try:
                read_new(dev["id"])
            except OSError as e:
                print(f"[SCAN] {dev['id']}: {e}", flush=True)
        build_status(now)
        return True


def _loop():
    while True:
        try:
            if _recently_active():
                scan_once(force=True)
        except Exception as e:
            print(f"[DASH] error en scan: {e}", flush=True)
        time.sleep(15)


# ---------------------------------------------------------------- payloads
def live_payload():
    """Un único request con todo lo que el grid necesita."""
    scan_once()
    devs = []
    for d in DEVICES:
        st = _status.get(d["id"], {})
        values = st.get("values") or {}
        mf = st.get("main_field")
        devs.append({
            "id": d["id"], "name": d["name"], "loc": d["loc"], "interval": d["interval"],
            "origin": d.get("origin", ""),
            "online": st.get("online", False), "values": values,
            "extremes": st.get("extremes", []), "points": st.get("points", 0),
            "main_field": mf, "series": _series(d["id"], mf, SPARK_N) if mf else [],
            "last_ts": st.get("last_ts"),
        })
    return {"now": _last_scan["ts"], "uptime_s": round(time.time() - _started_at, 1),
            "summary": _summary, "devices": devs}


def history_payload(dev_id, range_key="24h", max_pts=CHART_MAX, raw=False,
                    limit=None, frm=None, to=None):
    dev = DEV_BY_ID[dev_id]
    now = time.time()
    allpts = _buf.get(dev_id) or []
    if frm is not None or to is not None:
        lo = float(frm) if frm is not None else 0.0
        hi = float(to) if to is not None else now
        win = {"from": lo, "to": hi, "key": "custom"}
    elif range_key == "all":
        lo = allpts[0]["ts"] if allpts else now - 86400
        hi = max(now, allpts[-1]["ts"] if allpts else now) + 120
        win = {"from": lo, "to": hi, "key": "all"}
    else:
        secs = RANGES.get(range_key, 86400)
        # pequeño margen para lecturas con timestamp ligeramente por delante del servidor
        lo, hi = now - secs, now + 120
        win = {"from": lo, "to": hi, "key": range_key}

    pts = device_points(dev_id, after=lo, before=hi)
    if limit:
        pts = pts[-limit:]
    stats = window_stats(pts)
    total = len(pts)
    out = pts if raw else downsample_minmax(pts, max_pts)
    return {
        "ok": True, "id": dev_id, "name": dev["name"], "loc": dev["loc"],
        "interval": dev["interval"], "origin": dev.get("origin", ""),
        "window": win, "points": out, "count_total": total, "count_returned": len(out),
        "downsampled": (not raw) and len(out) < total, "stats": stats,
        "available": {"from": allpts[0]["ts"] if allpts else None,
                      "to": allpts[-1]["ts"] if allpts else None,
                      "count": len(allpts)},
    }


def export_csv(dev_id, range_key="all"):
    dev = DEV_BY_ID[dev_id]
    if range_key == "all":
        pts = list(_buf.get(dev_id) or [])
    else:
        pts = device_points(dev_id, after=time.time() - RANGES.get(range_key, 86400))
    keys = set()
    for p in pts:
        keys.update(k for k, v in p["v"].items() if k not in SKIP_FIELDS)
    cols = sorted(keys)
    lines = ["timestamp," + ",".join(cols)]
    for p in pts:
        row = [p.get("t") or ""]
        for c in cols:
            v = p["v"].get(c, "")
            if isinstance(v, str):
                v = '"' + v.replace('"', '""') + '"'
            row.append(str(v))
        lines.append(",".join(row))
    return f"device_{dev_id}_{range_key}.csv", "\n".join(lines) + "\n", len(pts)


def evidencias_payload():
    scan_once()
    now = time.time()
    flota = []
    total_pts = 0
    for d in DEVICES:
        pts = _buf.get(d["id"]) or []
        total_pts += len(pts)
        first = pts[0]["ts"] if pts else None
        last = pts[-1]["ts"] if pts else None
        values = read_latest(d["id"]) or {}
        gaps = detect_gaps(d)
        flota.append({
            "id": d["id"], "name": d["name"], "loc": d["loc"], "interval": d["interval"],
            "origin": d.get("origin", ""),
            "online": _online(d, now), "points": len(pts),
            "first_ts": first, "last_ts": last,
            "span_h": round((last - first) / 3600.0, 2) if first and last else 0,
            "values": values, "main_field": _main_field(values),
            "extremes": current_extremes(values),
            "gaps": gaps[-8:], "gaps_count": len(gaps),
        })
    dias = {}
    for p in (p for did in _buf for p in _buf[did]):
        dias[datetime.fromtimestamp(p["ts"], timezone.utc).strftime("%Y-%m-%d")] = True
    intervalos = sorted({d["interval"] for d in DEVICES})
    wokwi_last = _tail_lines(WOKWI_LOG, 1)
    wokwi_count = 0
    try:
        with open(WOKWI_LOG, encoding="utf-8", errors="replace") as fh:
            for _ in fh:
                wokwi_count += 1
    except OSError:
        pass
    return {
        "now": now, "id_scope": ID_SCOPE, "hub": IOT_HUB, "template": DEVICE_TEMPLATE,
        "flota": flota, "total_points": total_pts, "dias": sorted(dias.keys()),
        "intervalos": intervalos, "asincrono": len(intervalos) >= 3,
        "online": sum(1 for f in flota if f["online"]),
        "alerts": _summary.get("alerts", []), "dispatches": _dispatch_stats["count"],
        "wokwi": {"lines": wokwi_count, "last": wokwi_last[-1] if wokwi_last else None,
                  "file": WOKWI_LOG,
                  "bytes": (os.path.getsize(WOKWI_LOG) if os.path.exists(WOKWI_LOG) else 0)},
        "total_gaps": sum(f["gaps_count"] for f in flota),
        "uptime_s": round(now - _started_at, 1),
    }


# ---------------------------------------------------------------- recursos HTML
SHARED_CSS = """
  :root{
    --bg:#0b0f14;--bg2:#0e131a;--card:#141b24;--card2:#182130;--line:#26303e;--line2:#31414f;
    --txt:#e7eef6;--muted:#9fb0c3;--faint:#76909f;
    --ok:#3fb950;--off:#f85149;--warn:#d29922;--acc:#58a6ff;
    --okbg:#10301b;--offbg:#3a1a1a;--warnbg:#3a2a12;
  }
  *{box-sizing:border-box}
  html{scrollbar-color:var(--line2) var(--bg)}
  body{margin:0;font-family:ui-monospace,'Cascadia Mono','Segoe UI Mono',Menlo,Consolas,monospace;
       background:radial-gradient(1200px 400px at 50% -80px,var(--bg2),var(--bg));color:var(--txt);
       min-height:100vh}
  ::selection{background:rgba(88,166,255,.32)}
  a{color:var(--acc);text-decoration:none}
  :focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:4px}
  header{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:14px;flex-wrap:wrap;
         padding:13px 22px;background:rgba(11,15,20,.9);backdrop-filter:blur(8px);
         border-bottom:1px solid var(--line)}
  .brand{display:flex;align-items:center;gap:10px}
  h1{font-size:17px;margin:0;letter-spacing:.02em}
  h1 .sub{display:block;color:var(--faint);font-size:11px;font-weight:400;letter-spacing:.14em;text-transform:uppercase}
  .grow{flex:1}
  nav.top{display:flex;gap:6px}
  nav.top a{padding:7px 12px;border-radius:8px;border:1px solid var(--line);color:var(--muted);font-size:12px}
  nav.top a.active{background:var(--card2);color:var(--txt);border-color:var(--line2)}
  .sum{color:var(--muted);font-size:12px}
  #clock{color:var(--muted);font-size:12px;text-align:right}
  .btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:8px;cursor:pointer;
       font:600 13px/1 ui-monospace,Consolas,monospace;padding:9px 14px;transition:transform .12s,box-shadow .12s,filter .12s}
  .btn:hover{transform:translateY(-1px);filter:brightness(1.06)}
  .btn:disabled{opacity:.5;cursor:wait;transform:none}
  .btn-primary{background:var(--acc);color:#04121f}
  .btn-primary:not(:disabled){box-shadow:0 2px 14px rgba(88,166,255,.28)}
  .btn-ghost{background:var(--card2);color:var(--txt);border:1px solid var(--line2)}
  .panel2{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
  .panel2 h2{margin:0 0 12px;font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;font-weight:600}
  .pill{font-size:10px;padding:3px 8px;border-radius:99px;font-weight:700;letter-spacing:.08em;white-space:nowrap}
  .pill.on{background:var(--okbg);color:var(--ok)}
  .pill.off{background:var(--offbg);color:var(--off)}
  .pill.warn{background:var(--warnbg);color:var(--warn)}
  .seg{display:inline-flex;border:1px solid var(--line2);border-radius:8px;overflow:hidden;flex-wrap:wrap}
  .seg button{background:var(--card2);color:var(--muted);border:0;padding:7px 12px;font:600 11.5px/1 ui-monospace,Consolas,monospace;cursor:pointer}
  .seg button.active{background:var(--acc);color:#04121f}
  .segcl input{background:var(--card2);color:var(--txt);border:1px solid var(--line2);border-radius:8px;padding:6px 10px;font:600 11.5px/1 ui-monospace,Consolas,monospace}
  .logs{background:#0b0f14;border:1px solid var(--line);border-radius:10px;padding:12px;max-height:290px;overflow:auto;
        font:11px/1.5 ui-monospace,Consolas,Menlo,monospace;color:#b8d0e8;margin:0;white-space:pre-wrap;word-break:break-all}
  .hint{color:var(--faint);font-size:11px}
  table{width:100%;border-collapse:collapse;font-size:11.5px}
  th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}
  th{color:var(--faint);font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:10px}
  .scroll{max-height:420px;overflow:auto;border:1px solid var(--line);border-radius:10px}
  #toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:30;background:var(--card2);
         border:1px solid var(--line2);border-radius:10px;padding:10px 18px;font-size:12px;color:var(--txt);
         box-shadow:0 8px 30px rgba(0,0,0,.5);opacity:0;pointer-events:none;transition:opacity .25s}
  #toast.show{opacity:1}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
"""

SHARED_JS = """
const UNITS=%UNITS%;
const LABELS=%LABELS%;
const SKIP=new Set(['timestamp','api_source','source','device_id','csv_row','mqtt_status','ack_status','emergency_status','door_status','motion','ack_pending','_bridge','_source','_timestamp','disconnected_devices']);
function esc(s){return (s===null||s===undefined)?'':String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function fmtNum(v){if(typeof v!=='number')return esc(v);const a=Math.abs(v);return v.toFixed(a>=100?0:(a>=10?1:2));}
function fmtT(ts){const d=new Date(ts*1000);return d.toLocaleString('es-CO',{hour12:false});}
function fmtDur(s){if(s<90)return Math.round(s)+' s';if(s<5400)return (s/60).toFixed(1)+' min';if(s<172800)return (s/3600).toFixed(1)+' h';return (s/86400).toFixed(1)+' dias';}
function num(k){return LABELS[k]&&!SKIP.has(k);}
function loadScript(src){return new Promise((res,rej)=>{const s=document.createElement('script');s.src=src;s.onload=res;s.onerror=rej;document.head.appendChild(s);});}
async function ensureChart(){
  if(!window.Chart){await loadScript('https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js');}
  // el eje temporal (type:'time') EXIGE un adaptador de fechas en Chart.js v4
  if(!window.__chartAdapter){
    try{await loadScript('https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js');window.__chartAdapter=1;}catch(e){}
  }
}
function spark(canvas,pts,color,fill){
  if(!pts||pts.length<2)return;
  const dpr=window.devicePixelRatio||1;
  const w=canvas.clientWidth||canvas.parentElement.clientWidth||240,h=canvas.clientHeight||44;
  canvas.width=w*dpr;canvas.height=h*dpr;
  const g=canvas.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,w,h);
  const lo=Math.min.apply(null,pts),hi=Math.max.apply(null,pts),rn=(hi-lo)||1;
  const X=i=>i/(pts.length-1)*w, Y=v=>h-3-((v-lo)/rn)*(h-8);
  if(fill){const gr=g.createLinearGradient(0,0,0,h);gr.addColorStop(0,color+'55');gr.addColorStop(1,color+'00');
    g.beginPath();g.moveTo(0,h);pts.forEach((v,i)=>g.lineTo(X(i),Y(v)));g.lineTo(w,h);g.closePath();g.fillStyle=gr;g.fill();}
  g.beginPath();pts.forEach((v,i)=>i?g.lineTo(X(i),Y(v)):g.moveTo(X(i),Y(v)));
  g.strokeStyle=color;g.lineWidth=1.6;g.lineJoin='round';g.stroke();
  g.fillStyle=color;g.beginPath();g.arc(X(pts.length-1),Y(pts[pts.length-1]),2.2,0,7);g.fill();
}
function whenVisible(fn,ms){
  setInterval(()=>{if(!document.hidden)fn();},ms);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)fn();});
}
function tickClock(el){const u=()=>{if(el)el.textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});};u();setInterval(u,1000);}
function lineChart(canvas,rows,fieldLabel,unit,thr,limits,view){
  // si quedó una gráfica huérfana en el canvas (p.ej. un intento fallido), se libera
  if(window.Chart){const prev=Chart.getChart(canvas);if(prev)prev.destroy();}
  const ctx=canvas.getContext('2d');
  const ds=[{data:rows,label:fieldLabel,borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,.14)',fill:true,tension:.28,borderWidth:1.7,pointRadius:0,pointHitRadius:14}];
  if(thr&&rows.length){
    if(thr[1]!=null)ds.push({label:'umbral max',data:[{x:rows[0].x,y:thr[1]},{x:rows[rows.length-1].x,y:thr[1]}],borderColor:'#f85149',borderDash:[5,4],borderWidth:1,pointRadius:0});
    if(thr[0]!=null)ds.push({label:'umbral min',data:[{x:rows[0].x,y:thr[0]},{x:rows[rows.length-1].x,y:thr[0]}],borderColor:'#d29922',borderDash:[5,4],borderWidth:1,pointRadius:0});
  }
  const plugins={legend:{display:false},tooltip:{displayColors:false,callbacks:{
      label:c=>c.dataset.label+': '+fmtNum(c.parsed.y)+' '+unit,
      title:i=>i.length?fmtT(i[0].parsed.x/1000):''}}};
  return new Chart(ctx,{type:'line',data:{datasets:ds},options:{
    responsive:true,maintainAspectRatio:false,animation:false,
    interaction:{mode:'index',intersect:false},plugins:plugins,
    scales:{x:{type:'time',bounds:'data',min:view.lo,max:view.hi,ticks:{maxTicksLimit:10,color:'#76909f',font:{size:11}},grid:{color:'#1c2532'}},
            y:{ticks:{color:'#76909f',font:{size:11},callback:v=>v+' '+unit},grid:{color:'#1c2532'}}}}});
}

/* ---- ventana visible dentro de todo el historial cargado ---- */
const VIEW_SECS={'1h':3600,'6h':21600,'24h':86400,'72h':259200,'7d':604800};
function viewPoints(st){return st.all.filter(p=>p.ts*1000>=st.view.lo&&p.ts*1000<=st.view.hi);}
function viewStats(pts){
  const out={};
  pts.forEach(p=>Object.keys(p.v).forEach(k=>{
    if(!num(k))return;
    const v=p.v[k];
    if(typeof v!=='number')return;
    const cur=out[k]||(out[k]={count:0,min:null,max:null,sum:0,last:null,unit:UNITS[k]||'',label:LABELS[k]||k});
    cur.count++;cur.sum+=v;cur.min=cur.min==null?v:Math.min(cur.min,v);
    cur.max=cur.max==null?v:Math.max(cur.max,v);cur.last=v;
  }));
  Object.keys(out).forEach(k=>{out[k].avg=out[k].count?out[k].sum/out[k].count:null;});
  return out;
}
/* recorta la ventana para que nunca salga del rango con datos */
function clampView(st,lo,hi){
  const total=Math.max(60000,st.avail.to-st.avail.from);
  let span=Math.min(Math.max(hi-lo,60000),total);
  if(lo<st.avail.from)lo=st.avail.from;
  if(lo+span>st.avail.to)lo=st.avail.to-span;
  if(lo<st.avail.from)lo=st.avail.from;
  return {lo:lo,hi:lo+span};
}
function setViewOnChart(st,lo,hi){
  st.view=clampView(st,lo,hi);
  if(st.chart&&st.chart.scales.x){
    st.chart.options.scales.x.min=st.view.lo;
    st.chart.options.scales.x.max=st.view.hi;
    st.chart.update('none');
  }
}
function applyRange(st,r,now){
  st.range=r;now=now||Date.now();
  const secs=VIEW_SECS[r];
  let lo=secs?Math.max(st.avail.from,now-secs*1000):st.avail.from;
  if(lo>=st.avail.to)lo=st.avail.from;
  setViewOnChart(st,lo,st.avail.to);
}
function shiftView(st,back){
  const span=st.view.hi-st.view.lo;
  setViewOnChart(st,st.view.lo+span*(back?-0.9:0.9),st.view.hi+span*(back?-0.9:0.9));
}
function jumpView(st,t){
  const span=st.view.hi-st.view.lo;
  setViewOnChart(st,t-span/2,t+span/2);
}
/* arrastrar = mover en el tiempo · ctrl+rueda = zoom sobre todo el histórico */
function attachNav(canvas,st,onChange){
  let drag=null;
  canvas.style.cursor='grab';
  canvas.addEventListener('mousedown',e=>{
    drag={x:e.clientX,view:{lo:st.view.lo,hi:st.view.hi}};
    canvas.style.cursor='grabbing';e.preventDefault();
  });
  window.addEventListener('mousemove',e=>{
    if(!drag)return;
    const w=canvas.clientWidth||1,span=drag.view.hi-drag.view.lo;
    const d=(e.clientX-drag.x)/w*span;
    setViewOnChart(st,drag.view.lo-d,drag.view.hi-d);
    if(onChange)onChange();
  });
  window.addEventListener('mouseup',()=>{if(drag){drag=null;canvas.style.cursor='grab';}});
  canvas.addEventListener('wheel',e=>{
    if(!e.ctrlKey)return;
    e.preventDefault();
    const rect=canvas.getBoundingClientRect();
    const fx=Math.min(1,Math.max(0,(e.clientX-rect.left)/(rect.width||1)));
    const span=st.view.hi-st.view.lo,t=st.view.lo+fx*span;
    const ns=span*(e.deltaY>0?1.25:0.8);
    setViewOnChart(st,t-(t-st.view.lo)*(ns/span),t-(t-st.view.lo)*(ns/span)+ns);
    if(onChange)onChange();
  },{passive:false});
}
function drawSt(canvas,st,thr,onMove){
  const unit=UNITS[st.field]||'';
  const rows=st.all.map(p=>({x:p.ts*1000,y:p.v[st.field]})).filter(p=>typeof p.y==='number').sort((a,b)=>a.x-b.x);
  st.chart=lineChart(canvas,rows,LABELS[st.field]||st.field,unit,thr,
     {from:st.avail.from/1000,to:st.avail.to/1000},{lo:st.view.lo,hi:st.view.hi});
  st.chart.options.scales.x.min=st.view.lo;
  st.chart.options.scales.x.max=st.view.hi;
  st.chart.update('none');
  if(!canvas.__nav){attachNav(canvas,st,onMove);canvas.__nav=1;}
}
"""

ADVISOR_SVG = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 '
               '2 4.2 2 2 0 0 1 4 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8 10a16 16 0 0 0 6 6l1.3-1.2a2 2 0 0 1 '
               '2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z"/></svg>')

HEADER_TPL = """<header>
  <div class="brand" aria-hidden="true">
    <svg width="29" height="29" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="1.6">
      <rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 15l3-4 2 2 3-5"/>
    </svg>
  </div>
  <div><h1>%TITLE%<span class="sub">%SUBTITLE%</span></h1></div>
  <nav class="top">
    <a href="/"%NAV_HOME%>Sala de control</a>
    <a href="/evidencias"%NAV_EV%>Evidencias</a>
  </nav>
  <div class="grow"></div>
%EXTRA%
  <div id="clock">—</div>
</header>"""


def _header(title, subtitle, active, extra=""):
    return (HEADER_TPL
            .replace("%TITLE%", title).replace("%SUBTITLE%", subtitle)
            .replace("%NAV_HOME%", ' class="active"' if active == "home" else "")
            .replace("%NAV_EV%", ' class="active"' if active == "ev" else "")
            .replace("%EXTRA%", extra))


# ---------------------------------------------------------------- HTML: grid
PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Campus EMS — Sala de control</title>
<style>
%SHARED_CSS%
  main{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;padding:18px 22px 0}
  .card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 15px;
        cursor:pointer;transition:border-color .15s,transform .15s,box-shadow .15s;animation:rise .4s cubic-bezier(.2,.7,.2,1) both}
  .card:hover{border-color:var(--line2);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.35)}
  .card.warn{border-color:var(--warn)}
  .card.off{opacity:.78}
  .card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
  .name{font-weight:700;font-size:13px}
  .loc{color:var(--muted);font-size:11px;margin-top:2px}
  .spark{margin:12px 0 10px;height:44px;width:100%;display:block}
  .big{display:flex;align-items:baseline;gap:6px;font-size:11px;color:var(--faint)}
  .big b{color:var(--txt);font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
  .tags{margin-top:10px;display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11px;color:var(--muted)}
  .tags span b{color:var(--txt);font-variant-numeric:tabular-nums}
  .badge{display:flex;align-items:center;gap:6px;color:var(--warn);font-size:11px;margin-top:10px}
  .cardtools{display:flex;gap:8px;margin-top:12px;border-top:1px solid var(--line);padding-top:10px;align-items:center}
  .cardtools span{font-size:11px;color:var(--faint)}
  .cardtools .lnk{margin-left:auto;color:var(--acc);font-size:11px}
  footer{color:var(--faint);font-size:11px;padding:14px 22px 30px}
  .control{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;padding:0 22px}
  .counts{display:flex;gap:10px;flex-wrap:wrap}
  .count{flex:1;min-width:110px;background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
  .count .c{font-size:11px;color:var(--faint);letter-spacing:.08em;text-transform:uppercase}
  .count .n{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}
  .count.on .n{color:var(--ok)}.count.off .n{color:var(--off)}.count.un .n{color:var(--muted)}
  .alertslist{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px}
  .alertslist li{display:flex;align-items:center;gap:10px;background:var(--warnbg);border:1px solid var(--warn);border-radius:10px;padding:10px 12px;font-size:12px}
  .alertslist .none{color:var(--muted);background:none;border-color:var(--line)}
  .globalkpi{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px}
  .gk{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
  .gk .k{font-size:10px;color:var(--faint);letter-spacing:.1em;text-transform:uppercase}
  .gk .v{font-size:20px;font-weight:700;margin:5px 0 2px;font-variant-numeric:tabular-nums}
  .gk .s{font-size:10px;color:var(--muted)}
  .zones{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}
  .zone{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:11px}
  .zone b{display:block;font-size:12px;margin-bottom:3px}
  .zone .st{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
  .zone .st.on{background:var(--ok)}.zone .st.off{background:var(--off)}.zone .st.warn{background:var(--warn)}
  details.wokwi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
  details.wokwi summary{cursor:pointer;font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;font-weight:600}
  details.wokwi[open] summary{margin-bottom:12px}
  details.wokwi .meta{color:var(--faint);font-size:11px;margin-bottom:8px}
  dialog#dlg{border:1px solid var(--line2);border-radius:14px;background:var(--bg);color:var(--txt);padding:0;
             width:min(1180px,96vw);max-height:94vh;box-shadow:0 30px 80px rgba(0,0,0,.6)}
  dialog#dlg::backdrop{background:rgba(3,6,10,.72);backdrop-filter:blur(2px)}
  .mhead{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:14px 18px;border-bottom:1px solid var(--line);
         position:sticky;top:0;background:rgba(11,15,20,.97);z-index:3}
  .mhead h2{margin:0;font-size:15px}
  .mhead .id{color:var(--acc)}
  .mhead .loc{color:var(--muted);font-size:11px}
  .mbody{padding:16px 18px 22px}
  .mtools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  .chartwrap{position:relative;height:44vh;min-height:280px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px 6px}
  .chartwrap canvas{position:absolute;inset:0}
  .stats{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
  .stats b{color:var(--txt)}
  .readout{font-size:11.5px;color:var(--acc);font-variant-numeric:tabular-nums;white-space:nowrap}
  .kpirow{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px;margin-bottom:16px}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
  .kpi .k{color:var(--faint);font-size:10px;letter-spacing:.12em;text-transform:uppercase}
  .kpi .v{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums;margin:5px 0 2px}
  .kpi .r{font-size:10px;color:var(--muted)}
</style></head>
<body>
<div id="toast" role="status" aria-live="polite"></div>
%HEADER%

<section class="control" style="padding-top:18px">
  <div class="panel2">
    <h2>Estado de la flota</h2>
    <div class="counts">
      <div class="count on"><div class="c">Conectados</div><div class="n" id="cOn">—</div></div>
      <div class="count off"><div class="c">Desconectados</div><div class="n" id="cOff">—</div></div>
      <div class="count un"><div class="c">Total</div><div class="n" id="cTot">—</div></div>
    </div>
  </div>
  <div class="panel2">
    <h2>Alertas activas</h2>
    <ul class="alertslist" id="alerts"><li class="none">Sin alertas</li></ul>
  </div>
</section>

<section class="control" style="padding-top:14px">
  <div class="panel2" style="grid-column:1/-1">
    <h2>KPIs de la flota · último / mín / máx (ahora mismo)</h2>
    <div class="globalkpi" id="globalkpi"></div>
  </div>
</section>

<section class="control" style="padding-top:14px">
  <div class="panel2" style="grid-column:1/-1">
    <h2>Mapa de zonas</h2>
    <div class="zones" id="zones"></div>
  </div>
</section>

<main id="grid"></main>

<div style="padding:16px 22px 0">
  <details class="wokwi" id="wokwid">
    <summary>Wokwi D2 · Serial en vivo (se carga solo al abrir)</summary>
    <div class="meta" id="wokwimeta">—</div>
    <pre class="logs" id="wokwilogs">Abre este panel para cargar el log del simulador…</pre>
  </details>
</div>

<footer id="foot">Cargando…</footer>

<dialog id="dlg" aria-label="Histórico del dispositivo">
  <div class="mhead">
    <h2><span class="id" id="dId">—</span> · <span id="dName">—</span></h2>
    <span class="loc" id="dLoc">—</span>
    <span class="pill" id="dPill">…</span>
    <div class="grow"></div>
    <span class="readout" id="dWin">—</span>
    <a class="btn btn-ghost" id="dFull" href="#">Vista completa</a>
    <a class="btn btn-ghost" id="dCsv" href="#">CSV</a>
    <button class="btn btn-ghost" id="dClose" type="button">Cerrar ✕</button>
  </div>
  <div class="mbody">
    <div class="mtools">
      <div class="seg" id="dFields" role="group" aria-label="Métrica"></div>
      <div class="seg" id="dRanges" role="group" aria-label="Ventana">
        <button type="button" data-r="1h">1h</button>
        <button type="button" data-r="6h">6h</button>
        <button type="button" data-r="24h" class="active">24h</button>
        <button type="button" data-r="72h">72h</button>
        <button type="button" data-r="7d">7d</button>
        <button type="button" data-r="all">todo</button>
      </div>
      <div class="seg" role="group" aria-label="Navegar en el tiempo">
        <button type="button" id="dPrev" title="Ventana anterior">&lt;</button>
        <button type="button" id="dNext" title="Ventana siguiente">&gt;</button>
        <button type="button" id="dHome" title="Volver al presente">●</button>
      </div>
      <div class="segcl"><input type="datetime-local" id="dJump" aria-label="Ir a fecha y hora"></div>
      <span class="hint">arrastrar: mover · ctrl+rueda: zoom</span>
    </div>
    <div class="chartwrap"><canvas id="dChart" role="img" aria-label="Histórico del dispositivo"></canvas></div>
    <div class="stats">
      <span>último <b id="sLast">—</b></span><span>mín <b id="sMin">—</b></span><span>pico <b id="sMax">—</b></span>
      <span>prom <b id="sAvg">—</b></span><span>suma <b id="sSum">—</b></span><span>lecturas <b id="sN">—</b></span>
      <span class="hint" id="sDown"></span>
    </div>
    <h2 style="font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;margin:18px 0 10px">
      Resumen de la ventana <span class="hint">(todas las métricas del dispositivo)</span>
    </h2>
    <div class="kpirow" id="dKpis"></div>
    <h2 style="font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;margin:18px 0 10px">
      Últimos registros
    </h2>
    <div class="scroll" style="max-height:28vh"><table><thead><tr><th>Hora</th><th>Lectura</th></tr></thead><tbody id="dRows"></tbody></table></div>
    <h2 style="font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;margin:18px 0 10px">
      Log del dispositivo
    </h2>
    <pre class="logs" id="dLogs">—</pre>
  </div>
</dialog>

<script>
%SHARED_JS%
const $=id=>document.getElementById(id);
const grid=$('grid'),foot=$('foot'),sum=$('sum'),adv=$('advisor');
const state={range:'24h',field:null,all:[],view:{lo:0,hi:1},avail:{from:0,to:1},chart:null,dev:null,timer:null,loading:false};
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),3500);}

/* ---------- grid: UN request alimenta todo ---------- */
async function loadLive(){
  let j;
  try{ j=await (await fetch('/api/live')).json(); }
  catch(e){ foot.textContent='Sin conexion con el servidor del dashboard.'; return; }
  const devs=j.devices||[],s=j.summary||{};
  sum.textContent=(s.online||0)+' de '+(s.total||devs.length)+' en linea';
  $('cOn').textContent=s.online;$('cOff').textContent=s.offline;$('cTot').textContent=s.total;
  const el=$('alerts');
  if(s.alerts&&s.alerts.length){
    el.innerHTML=s.alerts.map(a=>'<li><b>'+esc(a.id)+'</b> '+esc(a.name)+' — '+a.extremes.map(k=>esc(LABELS[k]||k)).join(', ')+'</li>').join('');
  }else{el.innerHTML='<li class="none">Sin alertas activas</li>';}
  const kg=$('globalkpi');kg.innerHTML='';
  ['temperature','humidity','pm25','co2_sim','aqi','co_level','pressure','sound_level','lux','wind_speed'].forEach(k=>{
    const d=(s.kpis||{})[k];if(!d)return;
    const div=document.createElement('div');div.className='gk';
    div.innerHTML='<div class="k">'+esc(LABELS[k])+'</div><div class="v">'+fmtNum(d.last)+' <span style="font-size:11px;color:var(--muted)">'+esc(UNITS[k]||'')+'</span></div>'
      +'<div class="s">min '+fmtNum(d.min)+' · max '+fmtNum(d.max)+' · prom '+fmtNum(d.avg)+'</div>';
    kg.appendChild(div);
  });
  $('zones').innerHTML=devs.map(d=>{
    const st=((d.extremes||[]).length&&d.online)?'warn':(d.online?'on':'off');
    return '<div class="zone"><b>'+esc(d.id)+' · '+esc(d.name)+'</b><div><span class="st '+st+'"></span>'+esc(d.loc)+' · '+(d.online?'CONECTADO':'OFFLINE')+((d.extremes||[]).length?' · ALERTA':'')+'</div></div>';
  }).join('');
  grid.innerHTML=devs.map(d=>{
    const warn=(d.extremes||[]).length, mf=d.main_field;
    const last=mf?(fmtNum(d.values[mf])+' '+esc(UNITS[mf]||'')):'—';
    const tags=Object.keys(d.values).filter(k=>num(k)&&k!==mf).slice(0,4)
      .map(k=>'<span>'+esc(LABELS[k])+': <b>'+fmtNum(d.values[k])+' '+esc(UNITS[k]||'')+'</b></span>').join('');
    return '<article class="card'+(warn?' warn':'')+(d.online?'':' off')+'" tabindex="0" role="button" data-dev="'+esc(d.id)+'">'
      +'<div class="top"><div><div class="name">'+esc(d.id)+' · '+esc(d.name)+'</div>'
      +'<div class="loc">'+esc(d.loc)+' · interv. '+d.interval+'s · '+d.points+' lecturas</div></div>'
      +'<span class="pill '+(d.online?'on':'off')+'">'+(d.online?'CONECTADO':'OFFLINE')+'</span></div>'
      +'<canvas class="spark" data-dev="'+esc(d.id)+'"></canvas>'
      +'<div class="big"><b>'+last+'</b><span>'+(mf?esc(LABELS[mf]||mf):'sin telemetria')+'</span></div>'
      +(tags?'<div class="tags">'+tags+'</div>':'')
      +(warn?'<div class="badge">Alerta: '+d.extremes.map(k=>esc(LABELS[k]||k)).join(', ')+'</div>':'')
      +'<div class="cardtools"><span>historial: '+d.points+' lecturas</span>'
      +'<a class="lnk" href="/device/'+esc(d.id)+'">detalle completo</a></div></article>';
  }).join('');
  grid.querySelectorAll('.card').forEach(c=>{
    c.addEventListener('click',()=>openDevice(c.dataset.dev));
    c.addEventListener('keydown',e=>{if(e.key==='Enter')openDevice(c.dataset.dev);});
  });
  devs.forEach(d=>{
    const c=grid.querySelector('canvas.spark[data-dev="'+d.id+'"]');
    if(c)spark(c,d.series,(d.extremes||[]).length?'#d29922':(d.online?'#58a6ff':'#f85149'),true);
  });
  foot.textContent='Actualizado '+new Date().toLocaleTimeString('es-CO')+' · un solo request (/api/live) para toda la sala';
}
$('advisor').addEventListener('click',async e=>{
  const btn=e.currentTarget,old=btn.innerHTML;btn.disabled=true;btn.innerHTML='Enviando…';
  try{const j=await (await fetch('/api/dispatch',{method:'POST'})).json();toast(j.message);}
  catch(e2){toast('No se pudo enviar el despacho.');}
  setTimeout(()=>{btn.disabled=false;btn.innerHTML=old;},1500);
});

/* ---------- modal: historial del dispositivo ---------- */
function openDevice(id){
  state.dev=id;state.range='24h';state.field=null;state.all=[];state.stats={};
  $('dId').textContent=id;$('dFull').href='/device/'+id;
  document.querySelectorAll('#dRanges button').forEach(x=>x.classList.toggle('active',x.dataset.r===state.range));
  if(!$('dlg').open)$('dlg').showModal();
  if(state.timer)clearInterval(state.timer);
  state.timer=setInterval(loadLogs,5000);
  loadHist();loadLogs();
}
$('dClose').addEventListener('click',()=>$('dlg').close());
$('dlg').addEventListener('close',()=>{
  if(state.timer){clearInterval(state.timer);state.timer=null;}
  if(state.chart){state.chart.destroy();state.chart=null;}
});
$('dlg').addEventListener('click',e=>{if(e.target===$('dlg'))$('dlg').close();});
document.querySelectorAll('#dRanges button').forEach(b=>b.addEventListener('click',()=>{
  state.range=b.dataset.r;
  document.querySelectorAll('#dRanges button').forEach(x=>x.classList.toggle('active',x.dataset.r===state.range));
  applyRange(state,state.range);updateWin();syncStats();
}));
async function loadHist(){
  if(state.loading)return;
  state.loading=true;
  const id=state.dev;
  try{
    // UN solo request: trae TODO el histórico (con downsample que conserva picos).
    // Los botones de rango solo hacen zoom sobre lo ya cargado.
    const j=await (await fetch('/api/history?id='+id+'&range=all&max=2500')).json();
    state.all=j.points||[];
    state.avail={from:Math.max(0,(j.available.from||0)*1000-60000),
                 to:((j.available.to||Date.now()/1000)*1000)+60000};
    if(!j.points||!j.points.length){state.avail={from:Date.now()-86400000,to:Date.now()};}
    state.field=null;
    $('dName').textContent=j.name;
    $('dLoc').textContent=j.loc+' · interv. '+j.interval+'s · '+j.origin;
    $('dCsv').href='/api/export?id='+id+'&range=all';
    $('sDown').textContent=state.all.length+' lecturas cargadas'+(j.downsampled?(' de '+j.count_total+' (picos conservados)'):' (histórico completo)');
    const stats=viewStats(state.all);
    const fields=Object.keys(stats);
    if(fields.length)state.field=fields[0];
    const seg=$('dFields');seg.innerHTML='';
    fields.forEach(k=>{
      const b=document.createElement('button');b.type='button';b.textContent=LABELS[k]||k;b.dataset.f=k;
      if(k===state.field)b.classList.add('active');
      b.addEventListener('click',()=>{state.field=k;seg.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x.dataset.f===k));redraw();});
      seg.appendChild(b);
    });
    await ensureChart();
    applyRange(state,state.range);
    redraw();
  }catch(e){$('dLogs').textContent='Error cargando historico: '+e;}
  state.loading=false;
}
function redraw(){
  if(!state.field||!window.Chart)return;
  const thr=(%EXTREMES%)[state.field]||null;
  drawSt($('dChart'),state,thr,onViewChange);
  updateWin();syncStats();
}
function onViewChange(){ if(state.chart&&state.chart.scales.x){state.view={lo:state.chart.scales.x.min,hi:state.chart.scales.x.max};} updateWin();syncStats(); }
function updateWin(){
  $('dWin').textContent=fmtT(state.view.lo/1000)+' -> '+fmtT(state.view.hi/1000);
}
function syncStats(){
  const st=viewStats(viewPoints(state))[state.field];
  const u=UNITS[state.field]||'';
  if(!st){['sLast','sMin','sMax','sAvg','sSum','sN'].forEach(i=>$(i).textContent='—');return;}
  $('sLast').textContent=fmtNum(st.last)+' '+u;$('sMin').textContent=fmtNum(st.min)+' '+u;
  $('sMax').textContent=fmtNum(st.max)+' '+u;$('sAvg').textContent=fmtNum(st.avg)+' '+u;
  $('sSum').textContent=fmtNum(st.sum)+' '+u;$('sN').textContent=st.count;
  renderKpis();renderRows();
}
function renderKpis(){
  const el=$('dKpis');el.innerHTML='';
  const all=viewStats(viewPoints(state));
  Object.keys(all).forEach(k=>{
    const st=all[k],u=UNITS[k]||'';
    const d=document.createElement('div');d.className='kpi';
    d.innerHTML='<div class="k">'+esc(LABELS[k]||k)+'</div><div class="v">'+fmtNum(st.last)+'</div>'
      +'<div class="r">'+esc(u)+' · min '+fmtNum(st.min)+' · max '+fmtNum(st.max)+' · n '+st.count+'</div>';
    el.appendChild(d);
  });
}
function renderRows(){
  const pts=viewPoints(state);
  $('dRows').innerHTML=pts.slice(-60).reverse().map(p=>{
    const kv=Object.keys(p.v).filter(num).map(k=>LABELS[k]+'='+fmtNum(p.v[k])).join('  ');
    return '<tr><td>'+fmtT(p.ts)+'</td><td>'+kv+'</td></tr>';
  }).join('')||'<tr><td colspan="2">Sin datos en la ventana</td></tr>';
}
$('dPrev').addEventListener('click',()=>{shiftView(state,true);onViewChange();});
$('dNext').addEventListener('click',()=>{shiftView(state,false);onViewChange();});
$('dHome').addEventListener('click',()=>{applyRange(state,state.range);updateWin();syncStats();});
$('dJump').addEventListener('change',()=>{
  if(!$('dJump').value)return;
  jumpView(state,new Date($('dJump').value).getTime());
  onViewChange();
});
async function loadLogs(){
  if(!state.dev||document.hidden)return;
  try{
    const j=await (await fetch('/api/logs?id='+state.dev+'&n=120')).json();
    $('dLogs').textContent=(j.logs||[]).join('\\n')||'Sin lineas de log.';
  }catch(e){}
  try{
    const r=await (await fetch('/api/status')).json();
    const d=(r.devices||[]).filter(x=>x.id===state.dev)[0];
    if(d){$('dPill').textContent=d.online?'CONECTADO':'OFFLINE';$('dPill').className='pill '+(d.online?'on':'off');}
  }catch(e){}
}

/* ---------- panel Wokwi (carga diferida) ---------- */
let wokwiTimer=null;
$('wokwid').addEventListener('toggle',()=>{
  if($('wokwid').open){
    loadWokwi();
    if(!wokwiTimer)wokwiTimer=setInterval(()=>{if(!document.hidden)loadWokwi();},5000);
  }else if(wokwiTimer){clearInterval(wokwiTimer);wokwiTimer=null;}
});
async function loadWokwi(){
  try{
    const j=await (await fetch('/api/logs?src=wokwi&n=200')).json();
    $('wokwilogs').textContent=(j.logs||[]).join('\\n')||'Todavia no hay lineas. Ejecuta el ESP32 en Wokwi (run_wokwi_logs) para verlas aqui.';
    $('wokwimeta').textContent='archivo '+j.file+' · '+(j.lines||0)+' lineas · '+((j.bytes||0)/1024).toFixed(1)+' KB';
  }catch(e){$('wokwilogs').textContent='No se pudo leer el log del simulador.';}
}

tickClock($('clock'));
loadLive();
whenVisible(loadLive,20000);
</script></body></html>"""


# ---------------------------------------------------------------- HTML: evidencias
EVIDENCIAS_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Evidencias — Campus EMS</title>
<style>
%SHARED_CSS%
  .wrap{max-width:1320px;margin:0 auto;padding:18px 22px 60px}
  .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}
  .kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
  .kv{background:var(--card2);border:1px solid var(--line);border-radius:10px;padding:11px 13px}
  .kv .k{font-size:10px;color:var(--faint);letter-spacing:.1em;text-transform:uppercase}
  .kv .v{font-size:19px;font-weight:700;margin-top:5px;font-variant-numeric:tabular-nums;word-break:break-word}
  .kv .s{font-size:10px;color:var(--muted);margin-top:2px}
  tbody tr:hover{background:var(--card2)}
  .ok{color:var(--ok)}.bad{color:var(--off)}.warnc{color:var(--warn)}
  .st{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
  .st.on{background:var(--ok)}.st.off{background:var(--off)}.st.warn{background:var(--warn)}
  ul.checks{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:8px;font-size:12px}
  ul.checks li{display:flex;gap:10px;align-items:flex-start;padding:9px 11px;border:1px solid var(--line);border-radius:10px;background:var(--card2)}
  ul.checks li .ic{flex:none;font-weight:700}
  .foot{color:var(--faint);font-size:11px;margin-top:22px}
  @media print{body{background:#fff;color:#000}header{position:static}*{color:#000 !important}}
</style></head>
<body>
%HEADER%
<div class="wrap">
  <section class="panel2" style="margin-bottom:14px">
    <h2>Identidad del despliegue</h2>
    <div class="kpis" id="ident"></div>
  </section>
  <section class="panel2" style="margin-bottom:14px">
    <h2>Cobertura de datos (todo lo capturado)</h2>
    <div class="kpis" id="cover"></div>
  </section>
  <div class="grid2" style="margin-bottom:14px">
    <section class="panel2">
      <h2>Checklist del entregable (evaluado con datos reales)</h2>
      <ul class="checks" id="checks"></ul>
    </section>
    <section class="panel2">
      <h2>Estadísticas sobre el histórico completo</h2>
      <div class="scroll"><table><thead><tr><th>Métrica</th><th>Dev</th><th>n</th><th>mín</th><th>máx</th><th>prom</th><th>suma</th></tr></thead><tbody id="stats"></tbody></table></div>
    </section>
  </div>
  <section class="panel2" style="margin-bottom:14px">
    <h2>Flota · origen, intervalo y continuidad</h2>
    <div class="scroll"><table>
      <thead><tr><th>Dev</th><th>Dispositivo</th><th>Zona</th><th>Origen</th><th>Interv.</th>
      <th>Estado</th><th>Lecturas</th><th>Primera</th><th>Última</th><th>Cobertura</th><th>Cortes</th></tr></thead>
      <tbody id="flota"></tbody></table></div>
  </section>
  <div class="grid2" style="margin-bottom:14px">
    <section class="panel2">
      <h2>Desconexiones controladas detectadas (huecos &gt; 3× intervalo)</h2>
      <div class="scroll"><table><thead><tr><th>Dev</th><th>Desde</th><th>Hasta</th><th>Duración</th></tr></thead><tbody id="gaps"></tbody></table></div>
    </section>
    <section class="panel2">
      <h2>Simulador Wokwi (D2)</h2>
      <div class="kpis" id="wokwi"></div>
      <h2 style="margin-top:16px">Últimas líneas del Serial Monitor</h2>
      <pre class="logs" id="wokwilogs">—</pre>
    </section>
  </div>
  <section class="panel2">
    <h2>Links de evidencia</h2>
    <p class="hint" style="margin:0 0 10px">Cada vista sirve como captura: histórico navegable por fecha y hora, estadísticas de la ventana completa y descarga CSV.</p>
    <div id="links" style="display:flex;gap:10px;flex-wrap:wrap"></div>
  </section>
  <div class="foot" id="foot">—</div>
</div>
<script>
%SHARED_JS%
const $=id=>document.getElementById(id);
function kv(k,v,s){return '<div class="kv"><div class="k">'+k+'</div><div class="v">'+v+'</div>'+(s?'<div class="s">'+s+'</div>':'')+'</div>';}
function ic(ok,txt,extra){return '<li><span class="ic '+(ok?'ok':'bad')+'">'+(ok?'OK':'X')+'</span><div>'+txt+(extra?'<div class="hint">'+extra+'</div>':'')+'</div></li>';}
function icw(ok,txt,extra){return '<li><span class="ic '+(ok?'ok':'warnc')+'">'+(ok?'OK':'…')+'</span><div>'+txt+(extra?'<div class="hint">'+extra+'</div>':'')+'</div></li>';}
async function load(){
  const j=await (await fetch('/api/evidencias')).json();
  $('ident').innerHTML=
    kv('Dispositivos',j.flota.length,'provisionados')+
    kv('ID Scope',esc(j.id_scope),'DPS')+
    kv('Device template',esc((j.template||'').split(' ')[0]),esc((j.template||'').split(' ')[1]||''))+
    kv('Hub',esc((j.hub||'iotc-371f401d.azure-devices.net').split('.')[0]),'azure-devices.net')+
    kv('En línea',j.online+' / '+j.flota.length,'ahora')+
    kv('Uptime del dashboard',fmtDur(j.uptime_s),'desde este arranque')+
    kv('Despachos enviados',j.dispatches,'correo Brevo');
  $('cover').innerHTML=
    kv('Lecturas capturadas',j.total_points,'en el histórico')+
    kv('Días con datos',j.dias.length,(j.dias[0]||'—')+' → '+(j.dias[j.dias.length-1]||'—'))+
    kv('Intervalos distintos',j.intervalos.length,j.intervalos.join(' / ')+' s')+
    kv('Asincronía',j.asincrono?'SI':'NO','la guía pide >= 3 intervalos')+
    kv('Cortes detectados',j.total_gaps,'huecos > 3x intervalo')+
    kv('Líneas Wokwi',j.wokwi.lines,'Serial del ESP32');
  const conApi=j.flota.filter(f=>f.origin.indexOf('API')>=0).length;
  const conWokwi=j.flota.filter(f=>f.origin.indexOf('Wokwi')>=0).length;
  const che=[];
  che.push(ic(j.flota.length===10,'10 dispositivos en la flota','D1-D10 registrados en IoT Central'));
  che.push(ic(j.online>=8,j.online+' de 10 enviando telemetría en vivo','recalculado en cada carga'));
  che.push(ic(j.asincrono,'Intervalos de muestreo asincrónicos',j.intervalos.join(', ')+' segundos'));
  che.push(ic(j.total_points>0,'Histórico persistido y navegable',j.total_points+' lecturas en '+j.dias.length+' día(s)'));
  che.push(ic(j.total_gaps>0,'Resiliencia: corte y reconexión registrados',j.total_gaps+' hueco(s) en el histórico'));
  che.push(icw(j.wokwi.lines>0,'Logs del simulador Wokwi capturados',j.wokwi.lines+' líneas en '+j.wokwi.file));
  che.push(icw(conApi>0,'Datos de APIs públicas integrados',conApi+' nodo(s) con origen API'));
  che.push(icw(conWokwi>0,'Nodo Wokwi (ESP32) en la flota',conWokwi+' nodo; el bridge reenvía a IoT Central'));
  che.push(icw(j.dias.length>=4,'4 días no consecutivos de histórico','hoy hay '+j.dias.length+' día(s)'));
  $('checks').innerHTML=che.join('');

  $('flota').innerHTML=j.flota.map(f=>{
    const st=(f.extremes||[]).length?'warn':(f.online?'on':'off');
    return '<tr><td>'+esc(f.id)+'</td><td>'+esc(f.name)+'</td><td>'+esc(f.loc)+'</td><td>'+esc(f.origin)+'</td>'
      +'<td>'+f.interval+'s</td><td><span class="st '+st+'"></span>'+(f.online?'conectado':'sin telemetría')+((f.extremes||[]).length?' · ALERTA':'')+'</td>'
      +'<td>'+f.points+'</td><td>'+(f.first_ts?fmtT(f.first_ts):'—')+'</td><td>'+(f.last_ts?fmtT(f.last_ts):'—')+'</td>'
      +'<td>'+(f.span_h?f.span_h+' h':'—')+'</td><td>'+(f.gaps_count?('<span class="warnc">'+f.gaps_count+'</span>'):'0')+'</td></tr>';
  }).join('');

  const gaps=[];
  j.flota.forEach(f=>(f.gaps||[]).forEach(g=>gaps.push(g)));
  gaps.sort((a,b)=>b.from_ts-a.from_ts);
  $('gaps').innerHTML=gaps.length?gaps.map(g=>'<tr><td>'+esc(g.dev||'')+'</td><td>'+fmtT(g.from_ts)+'</td><td>'+fmtT(g.to_ts)+'</td><td>'+fmtDur(g.seconds)+'</td></tr>').join('')
    :'<tr><td colspan="4">Todavía no hay cortes mayores a 3x el intervalo.</td></tr>';

  const rows=[];
  j.flota.forEach(f=>{
    if(!f.main_field)return;
    Object.keys(f.values||{}).slice(0,6).forEach(k=>{
      if(!num(k)||typeof f.values[k]!=='number')return;
      rows.push('<tr><td>'+esc(LABELS[k]||k)+'</td><td>'+esc(f.id)+'</td><td>—</td><td>—</td><td>—</td><td>—</td><td>'+fmtNum(f.values[k])+'</td></tr>');
    });
  });
  $('stats').innerHTML=rows.join('')||'<tr><td colspan="7">Cargando…</td></tr>';

  $('wokwi').innerHTML=kv('Líneas capturadas',j.wokwi.lines,'wokwi_d2.log')
    +kv('Tamaño',(j.wokwi.bytes/1024).toFixed(1)+' KB','rotación a 5 MB')
    +kv('Última línea',j.wokwi.last?esc(String(j.wokwi.last).slice(11,42)):'—','UTC');
  try{
    const w=await (await fetch('/api/logs?src=wokwi&n=40')).json();
    $('wokwilogs').textContent=(w.logs||[]).join('\\n')||'Sin líneas todavía: ejecuta el ESP32 en Wokwi (run_wokwi_logs.bat).';
  }catch(e){}

  $('links').innerHTML=j.flota.map(f=>'<a class="btn btn-ghost" href="/device/'+esc(f.id)+'">'+esc(f.id)+' · '+esc(f.name)+'</a>').join('')
    +'<a class="btn btn-ghost" href="/api/export?id=01&range=all">CSV D1 (todo)</a>'
    +'<a class="btn btn-ghost" href="/api/export?id=02&range=all">CSV D2 Wokwi</a>';
  $('foot').textContent='Generado '+new Date().toLocaleString('es-CO')+' · datos en vivo desde ~/iotlogs (flota Python + simulador Wokwi + Azure IoT Central).';
}
$('refresh').addEventListener('click',load);
tickClock($('clock'));
load();
setInterval(()=>{if(!document.hidden)load();},60000);
</script></body></html>"""


# ---------------------------------------------------------------- HTML: detalle
DETAIL_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>%ID% · %NAME% — Campus EMS</title>
<style>
%SHARED_CSS%
  .back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:12px;padding:6px 10px;border-radius:8px;border:1px solid var(--line)}
  .back:hover{color:var(--txt);border-color:var(--line2)}
  .wrap{max-width:1240px;margin:0 auto;padding:18px 22px 60px}
  .alrt{display:none}
  .alrt.show{display:flex;gap:12px;align-items:flex-start;background:var(--offbg);border:1px solid var(--off);
             border-radius:12px;padding:14px 16px;margin-bottom:16px;animation:rise .3s cubic-bezier(.2,.7,.2,1) both}
  .alrt h3{margin:0 0 4px;color:#ffb3ae;font-size:13px}
  .kpirow{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:18px}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
  .kpi .k{color:var(--faint);font-size:10px;letter-spacing:.12em;text-transform:uppercase}
  .kpi .v{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums;margin:6px 0 2px}
  .kpi .u{font-size:12px;color:var(--muted)}
  .kpi .r{font-size:10px;color:var(--faint)}
  .toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;align-items:center}
  .chartbox{position:relative;height:330px}
  .stats{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
  .stats b{color:var(--txt)}
  .foot{margin-top:24px;color:var(--faint);font-size:11px;text-align:center}
</style></head>
<body>
%HEADER%
<div class="wrap">
  <div class="alrt" id="alrt">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2" aria-hidden="true" style="flex:none;margin-top:2px"><path d="M12 3 2 20h20L12 3z"/><path d="M12 9v5"/><path d="M12 17.5v.5"/></svg>
    <div style="flex:1"><h3>Lectura extrema detectada</h3><p id="alrtmsg" style="margin:0;color:var(--txt);font-size:12px"></p></div>
  </div>
  <div class="kpirow" id="kpis"></div>
  <div class="panel2" style="margin-bottom:18px">
    <h2>Trackeo histórico · <span id="histlen">…</span></h2>
    <div class="toolbar">
      <div class="seg" id="fields" role="group" aria-label="Métrica"></div>
      <div class="seg" id="ranges" role="group" aria-label="Rango de tiempo">
        <button type="button" data-r="1h">1h</button><button type="button" data-r="6h">6h</button>
        <button type="button" data-r="24h" class="active">24h</button><button type="button" data-r="72h">72h</button>
        <button type="button" data-r="7d">7d</button><button type="button" data-r="all">todo</button>
      </div>
      <a class="btn btn-ghost" href="/chart/%ID%">Métrica ampliada (zoom/fecha)</a>
      <button class="btn btn-ghost" id="reload" type="button">Actualizar histórico</button>
      <span class="hint" id="downinfo"></span>
    </div>
    <div class="chartbox"><canvas id="chart"></canvas></div>
    <div class="stats">
      <span>último <b id="sLast">—</b></span><span>mín <b id="sMin">—</b></span><span>pico <b id="sMax">—</b></span>
      <span>prom <b id="sAvg">—</b></span><span>suma <b id="sSum">—</b></span><span>lecturas <b id="sN">—</b></span>
    </div>
  </div>
  <div class="panel2">
    <h2>Registros de la ventana</h2>
    <div class="scroll" style="max-height:420px"><table><thead><tr><th>Hora</th><th>Lectura</th></tr></thead><tbody id="rows"></tbody></table></div>
    <button class="btn btn-ghost" id="more" type="button" style="margin-top:12px">Cargar historial completo (crudo)</button>
  </div>
  <div class="panel2" style="margin-top:18px">
    <h2>Log del dispositivo · en vivo</h2>
    <pre class="logs" id="logs">Cargando…</pre>
  </div>
  <div class="foot">Campus EMS · datos vía Azure IoT Central · se refresca cada 30 s (solo la ventana visible)</div>
</div>
<script>
%SHARED_JS%
const $=id=>document.getElementById(id);
const ID='%ID%';
const state={range:'24h',field:null,all:[],view:{lo:0,hi:1},avail:{from:0,to:1},chart:null};
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),3500);}
async function loadHist(){
  // UN request: todo el histórico (downsample conservando picos). Los rangos
  // son solo zoom sobre lo ya cargado; el historial crudo se pide a demanda.
  const j=await (await fetch('/api/history?id='+ID+'&range=all&max=2500')).json();
  state.all=j.points||[];
  state.avail={from:Math.max(0,(j.available.from||0)*1000-60000),to:((j.available.to||Date.now()/1000)*1000)+60000};
  if(!state.all.length)state.avail={from:Date.now()-86400000,to:Date.now()};
  $('histlen').textContent=j.available.count+' lecturas en total';
  $('downinfo').textContent=j.downsampled?(state.all.length+' de '+j.count_total+' puntos (picos conservados)'):(j.count_total+' puntos');
  const st=viewStats(state.all);
  const fields=Object.keys(st);
  if(!state.field||fields.indexOf(state.field)<0)state.field=fields[0]||null;
  const seg=$('fields');seg.innerHTML='';
  fields.forEach(k=>{
    const b=document.createElement('button');b.type='button';b.textContent=LABELS[k]||k;b.dataset.f=k;
    if(k===state.field)b.classList.add('active');
    b.addEventListener('click',()=>{state.field=k;seg.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x.dataset.f===k));redraw();});
    seg.appendChild(b);
  });
  await ensureChart();
  applyRange(state,state.range);
  redraw();
}
function redraw(){ if(!state.field||!window.Chart)return; drawSt($('chart'),state,(%EXTREMES%)[state.field]||null,onViewChange); syncStats(); }
function onViewChange(){ if(state.chart&&state.chart.scales.x)state.view={lo:state.chart.scales.x.min,hi:state.chart.scales.x.max}; syncStats(); }
function syncStats(){
  const all=viewStats(viewPoints(state));
  const st=all[state.field],u=UNITS[state.field]||'';
  if(st){
    $('sLast').textContent=fmtNum(st.last)+' '+u;$('sMin').textContent=fmtNum(st.min)+' '+u;
    $('sMax').textContent=fmtNum(st.max)+' '+u;$('sAvg').textContent=fmtNum(st.avg)+' '+u;
    $('sSum').textContent=fmtNum(st.sum)+' '+u;$('sN').textContent=st.count;
  }
  drawCards(all);renderRows();
}
function drawCards(all){
  all=all||viewStats(viewPoints(state));
  const el=$('kpis');el.innerHTML='';
  Object.keys(all).forEach(k=>{
    const st=all[k],u=UNITS[k]||'';
    const d=document.createElement('div');d.className='kpi';
    d.innerHTML='<div class="k">'+esc(LABELS[k]||k)+'</div><div class="v">'+fmtNum(st.last)+'</div><div class="u">'+esc(u)+'</div>'
      +'<div class="r">min '+fmtNum(st.min)+' · max '+fmtNum(st.max)+' · n '+st.count+'</div>';
    el.appendChild(d);
  });
}
function renderRows(){
  $('rows').innerHTML=viewPoints(state).slice(-80).reverse().map(p=>{
    const kv=Object.keys(p.v).filter(num).map(k=>LABELS[k]+'='+fmtNum(p.v[k])).join('  ');
    return '<tr><td>'+fmtT(p.ts)+'</td><td>'+kv+'</td></tr>';
  }).join('')||'<tr><td colspan="2">Sin datos en la ventana</td></tr>';
}
document.querySelectorAll('#ranges button').forEach(b=>b.addEventListener('click',()=>{
  state.range=b.dataset.r;
  document.querySelectorAll('#ranges button').forEach(x=>x.classList.toggle('active',x.dataset.r===state.range));
  applyRange(state,state.range);syncStats();
}));
$('more').addEventListener('click',async()=>{
  $('more').disabled=true;$('more').textContent='Cargando historial completo…';
  try{
    const j=await (await fetch('/api/history?id='+ID+'&raw=1&range=all')).json();
    state.all=j.points||[];
    applyRange(state,state.range);redraw();
    $('downinfo').textContent=state.all.length+' puntos crudos (sin downsample)';
    $('more').textContent='Histórico completo cargado ('+state.all.length+')';
  }catch(e){$('more').textContent='Error cargando';$('more').disabled=false;}
});
async function refreshLive(){
  if(document.hidden)return;
  try{
    const r=await (await fetch('/api/status')).json();
    const d=(r.devices||[]).filter(x=>x.id===ID)[0];
    if(d){
      $('pill').textContent=d.online?'CONECTADO':'OFFLINE';
      $('pill').className='pill '+(d.online?'on':'off');
      const n=(d.extremes||[]).length;
      if(n){$('alrt').classList.add('show');
        $('alrtmsg').textContent='En '+d.name+' ('+d.loc+'): '+d.extremes.map(k=>LABELS[k]||k).join(', ')+'. El asesor debe dirigirse a la ubicación señalada.';}
      else $('alrt').classList.remove('show');
    }
  }catch(e){}
  try{
    const j=await (await fetch('/api/logs?id='+ID+'&n=120')).json();
    $('logs').textContent=(j.logs||[]).join('\\n')||'Sin líneas de log.';
  }catch(e){}
}
$('adv').addEventListener('click',async e=>{
  const btn=e.currentTarget,old=btn.innerHTML;btn.disabled=true;btn.innerHTML='Enviando…';
  try{const j=await (await fetch('/api/dispatch?dev='+ID,{method:'POST'})).json();toast(j.message);}
  catch(e2){toast('No se pudo enviar el despacho.');}
  setTimeout(()=>{btn.disabled=false;btn.innerHTML=old;},1600);
});
$('csv').href='/api/export?id='+ID+'&range=all';
$('reload').addEventListener('click',async e=>{
  const b=e.currentTarget;b.disabled=true;const t=b.textContent;b.textContent='Cargando…';
  try{await loadHist();}catch(err){toast('Error recargando: '+err);}
  b.disabled=false;b.textContent=t;
});
tickClock($('clock'));
(async()=>{await loadHist();await refreshLive();
  // el histórico ya NO se re-pide cada 30 s: solo estado + logs (pidelo con "Actualizar")
  whenVisible(async()=>{await refreshLive();},30000);})();
</script></body></html>"""


# ---------------------------------------------------------------- HTML: ampliada
EXPAND_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>%ID% · %NAME% — Vista ampliada</title>
<style>
%SHARED_CSS%
  .back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:12px;padding:6px 10px;border-radius:8px;border:1px solid var(--line)}
  .back:hover{color:var(--txt);border-color:var(--line2)}
  .wrap{height:calc(100vh - 58px);display:flex;flex-direction:column;max-width:1520px;margin:0 auto;padding:14px 22px 20px;width:100%}
  .toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  .readout{font-size:11.5px;color:var(--acc);font-variant-numeric:tabular-nums;white-space:nowrap}
  .chartwrap{flex:1;position:relative;min-height:220px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px 8px}
  .chartwrap canvas{position:absolute;inset:0}
  .stats{display:flex;gap:20px;flex-wrap:wrap;margin-top:12px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
  .stats b{color:var(--txt)}
</style></head>
<body>
%HEADER%
<div class="wrap">
  <div class="toolbar">
    <div class="seg" id="fields" role="group" aria-label="Métrica"></div>
    <div class="seg" id="ranges" role="group" aria-label="Ventana de tiempo">
      <button type="button" data-r="1h">1h</button><button type="button" data-r="6h">6h</button>
      <button type="button" data-r="24h" class="active">24h</button><button type="button" data-r="72h">72h</button>
      <button type="button" data-r="7d">7d</button><button type="button" data-r="all">todo</button>
    </div>
    <div class="seg" role="group" aria-label="Navegar en el tiempo">
      <button type="button" id="prev" title="Ventana anterior">&lt;</button>
      <button type="button" id="next" title="Ventana siguiente">&gt;</button>
      <button type="button" id="home" title="Volver a la ventana actual">●</button>
    </div>
    <div class="segcl"><input type="datetime-local" id="jump" aria-label="Ir a fecha y hora"></div>
    <button class="btn btn-ghost" id="reload" type="button">Actualizar</button>
    <span class="hint">arrastrar: mover · ctrl+rueda: zoom</span>
    <span class="readout" id="win">—</span>
  </div>
  <div class="chartwrap"><canvas id="chart"></canvas></div>
  <div class="stats">
    <span>último <b id="s_last">—</b></span><span>mín <b id="s_min">—</b></span><span>pico <b id="s_pk">—</b></span>
    <span>prom <b id="s_avg">—</b></span><span>lecturas <b id="s_n">—</b></span><span>umbral <b id="s_thr">—</b></span>
    <span class="hint" id="dinfo"></span>
  </div>
</div>
<script>
%SHARED_JS%
const $=id=>document.getElementById(id);
const ID='%ID%';
const EXTREMES=%EXTREMES%;
const state={range:'24h',field:null,all:[],view:{lo:0,hi:1},avail:{from:0,to:1},chart:null};
function setHead(){
  const f=$('fld');
  if(f)f.textContent=LABELS[state.field]||state.field||'';
  const thr=EXTREMES[state.field];
  $('s_thr').textContent=thr?thr.map(x=>x==null?'—':x+' '+(UNITS[state.field]||'')).join(' · '):'sin umbral';
  $('s_thr').style.color=thr?'var(--warn)':'var(--faint)';
}
function redraw(){ if(!state.field||!window.Chart)return; drawSt($('chart'),state,EXTREMES[state.field]||null,onViewChange); syncStats(); }
function onViewChange(){ if(state.chart&&state.chart.scales.x)state.view={lo:state.chart.scales.x.min,hi:state.chart.scales.x.max}; syncStats(); }
function updateWin(){ $('win').textContent=fmtT(state.view.lo/1000)+' -> '+fmtT(state.view.hi/1000); }
function syncStats(){
  const all=viewStats(viewPoints(state));
  const st=all[state.field],u=UNITS[state.field]||'';
  if(st){$('s_last').textContent=fmtNum(st.last)+' '+u;$('s_min').textContent=fmtNum(st.min)+' '+u;
         $('s_pk').textContent=fmtNum(st.max)+' '+u;$('s_avg').textContent=fmtNum(st.avg)+' '+u;$('s_n').textContent=st.count;}
  updateWin();
}
async function load(){
  const j=await (await fetch('/api/history?id='+ID+'&range=all&max=3000')).json();
  state.all=j.points||[];
  state.avail={from:Math.max(0,(j.available.from||0)*1000-60000),to:((j.available.to||Date.now()/1000)*1000)+60000};
  if(!state.all.length)state.avail={from:Date.now()-86400000,to:Date.now()};
  if(j.available&&j.available.from)$('jump').min=new Date(j.available.from*1000).toISOString().slice(0,16);
  $('dinfo').textContent=j.count_total+' lecturas'+(j.downsampled?(' · dibujando '+state.all.length+' (picos conservados)'):'');
  const st=viewStats(state.all);
  const fields=Object.keys(st);
  if(!state.field||fields.indexOf(state.field)<0)state.field=fields[0]||null;
  const seg=$('fields');seg.innerHTML='';
  fields.forEach(k=>{
    const b=document.createElement('button');b.type='button';b.textContent=LABELS[k]||k;b.dataset.f=k;
    if(k===state.field)b.classList.add('active');
    b.addEventListener('click',()=>{state.field=k;seg.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x.dataset.f===k));setHead();redraw();});
    seg.appendChild(b);
  });
  setHead();applyRange(state,state.range);redraw();
}
document.querySelectorAll('#ranges button').forEach(b=>b.addEventListener('click',()=>{
  state.range=b.dataset.r;
  document.querySelectorAll('#ranges button').forEach(x=>x.classList.toggle('active',x.dataset.r===state.range));
  applyRange(state,state.range);syncStats();
}));
$('prev').addEventListener('click',()=>{shiftView(state,true);syncStats();});
$('next').addEventListener('click',()=>{shiftView(state,false);syncStats();});
$('home').addEventListener('click',()=>{applyRange(state,state.range);syncStats();});
$('jump').addEventListener('change',()=>{
  if(!$('jump').value)return;
  jumpView(state,new Date($('jump').value).getTime());
  syncStats();
});
tickClock($('clock'));
$('reload').addEventListener('click',async e=>{
  const b=e.currentTarget;b.disabled=true;const t=b.textContent;b.textContent='Cargando…';
  try{await load();}catch(err){}
  b.disabled=false;b.textContent=t;
});
(async()=>{await ensureChart();await load();
  setInterval(()=>{if(!document.hidden)updateWin();},1000);})();
</script></body></html>"""

_UNITS_JS = json.dumps(UNITS, ensure_ascii=False)
_LABELS_JS = json.dumps(LABELS, ensure_ascii=False)
_EXTREMES_JS = json.dumps({k: list(v) if v else None for k, v in EXTREMES.items()}, ensure_ascii=False)


def _prep(tpl):
    return (tpl
            .replace("%SHARED_CSS%", SHARED_CSS)
            .replace("%SHARED_JS%", SHARED_JS)
            .replace("%UNITS%", _UNITS_JS)
            .replace("%LABELS%", _LABELS_JS)
            .replace("%EXTREMES%", _EXTREMES_JS)
            .replace("%ADVISOR_SVG%", ADVISOR_SVG))


def fill_page(template, env):
    out = template
    for k, v in env.items():
        out = out.replace(k, v)
    return out


def grid_page():
    extra = ('<div class="sum" id="sum">—</div>'
             '<button class="btn btn-primary" id="advisor" type="button">' + ADVISOR_SVG + ' Llamar asesor</button>')
    return fill_page(_prep(PAGE), {"%HEADER%": _header("Campus EMS", "Sala de control · 10 dispositivos", "home", extra)})


def evidencias_page():
    extra = ('<button class="btn btn-ghost" onclick="window.print()" type="button">Imprimir / PDF</button>'
             '<button class="btn btn-ghost" id="refresh" type="button">Actualizar</button>')
    return fill_page(_prep(EVIDENCIAS_PAGE), {"%HEADER%": _header("Evidencias del parcial", "estado en vivo", "ev", extra)})


def detail_page(dev):
    sub = {"%ID%": dev["id"], "%NAME%": dev["name"], "%LOC%": dev["loc"],
           "%INTERVAL%": str(dev["interval"]), "%ORIGIN%": dev.get("origin", "")}
    extra = ('<span class="pill" id="pill">…</span>'
             '<a class="btn btn-ghost" href="/chart/%ID%">Vista ampliada</a>'
             '<a class="btn btn-ghost" id="csv" href="/api/export?id=%ID%&range=all">CSV</a>'
             '<button class="btn btn-primary" id="adv" type="button">' + ADVISOR_SVG + ' Llamar asesor</button>')
    head = fill_page(_header("%ID% · %NAME%", "%LOC% · intervalo %INTERVAL%s · %ORIGIN%", "home", extra), sub)
    env = dict(sub)
    env["%HEADER%"] = head
    return fill_page(_prep(DETAIL_PAGE), env)


def expand_page(dev):
    sub = {"%ID%": dev["id"], "%NAME%": dev["name"], "%LOC%": dev["loc"],
           "%INTERVAL%": str(dev["interval"])}
    extra = ('<a class="btn btn-ghost" href="/device/%ID%">Detalle</a>'
             '<a class="btn btn-ghost" href="/api/export?id=%ID%&range=all">CSV</a>')
    head = fill_page(_header("%ID% · %NAME%", "%LOC% · intervalo %INTERVAL%s", "home", extra), sub)
    env = dict(sub)
    env["%HEADER%"] = head
    return fill_page(_prep(EXPAND_PAGE), env)


# ---------------------------------------------------------------- HTTP
def _qs(path):
    q = {}
    if "?" in path:
        for kv in path.split("?", 1)[1].split("&"):
            if "=" in kv:
                k, _, v = kv.partition("=")
                q[k] = unquote_plus(v)
    return q


class H(http.server.BaseHTTPRequestHandler):
    server_version = "CampusEMS/2.0"
    protocol_version = "HTTP/1.1"

    def _send(self, data, ctype, code=200, extra=None):
        body = data.encode("utf-8") if isinstance(data, str) else data
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        self._send(json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8", code)

    def do_GET(self):
        path = self.path.split("?")[0]
        q = _qs(self.path)
        try:
            if path == "/":
                self._send(grid_page(), "text/html; charset=utf-8")
            elif path == "/evidencias":
                self._send(evidencias_page(), "text/html; charset=utf-8")
            elif path == "/api/live":
                _touch_activity()
                self._json(live_payload())
            elif path == "/api/status":
                _touch_activity()
                scan_once()
                self._json({"now": _last_scan["ts"], "summary": _summary,
                            "devices": [_status[k] for k in DEV_BY_ID if k in _status]})
            elif path == "/api/evidencias":
                _touch_activity()
                self._json(evidencias_payload())
            elif path == "/api/history":
                dev_id = q.get("id", "01")
                if dev_id not in DEV_BY_ID:
                    self._json({"ok": False, "message": "device no valido"}, 404)
                    return
                _touch_activity()
                scan_once()
                raw = q.get("raw") == "1"
                limit = int(q["limit"]) if q.get("limit") else None
                maxp = 0 if (raw or q.get("max") == "0") else int(q.get("max", CHART_MAX))
                frm, to = q.get("from"), q.get("to")
                self._json(history_payload(
                    dev_id, range_key=q.get("range", "24h"), max_pts=maxp, raw=raw,
                    limit=(None if limit in (None, 0) else limit),
                    frm=(float(frm) if frm else None), to=(float(to) if to else None)))
            elif path == "/api/export":
                dev_id = q.get("id", "01")
                if dev_id not in DEV_BY_ID:
                    self._json({"ok": False, "message": "device no valido"}, 404)
                    return
                scan_once()
                fname, csv, _n = export_csv(dev_id, q.get("range", "all"))
                self._send(csv, "text/csv; charset=utf-8",
                           extra={"Content-Disposition": 'attachment; filename="%s"' % fname})
            elif path == "/api/logs":
                n = max(1, min(600, int(q.get("n", "120"))))
                if q.get("src") == "wokwi":
                    logs = _tail_wokwi(n)
                    try:
                        lines_total = sum(1 for _ in open(WOKWI_LOG, encoding="utf-8", errors="replace"))
                    except OSError:
                        lines_total = len(logs)
                    self._json({"ok": True, "src": "wokwi", "logs": logs, "file": WOKWI_LOG,
                                "lines": lines_total,
                                "bytes": (os.path.getsize(WOKWI_LOG) if os.path.exists(WOKWI_LOG) else 0)})
                    return
                dev_id = q.get("id", "01")
                if dev_id not in DEV_BY_ID:
                    self._json({"ok": False, "message": "device no valido"}, 404)
                    return
                self._json({"ok": True, "src": "device", "id": dev_id, "logs": _tail_log(dev_id, n)})
            elif path.startswith("/chart/"):
                dev_id = path.rsplit("/", 1)[-1]
                if dev_id not in DEV_BY_ID:
                    self._send("<!doctype html><h1>Dispositivo no encontrado</h1><a href='/'>Inicio</a>",
                               "text/html; charset=utf-8", 404)
                    return
                self._send(expand_page(DEV_BY_ID[dev_id]), "text/html; charset=utf-8")
            elif path.startswith("/device/"):
                dev_id = path.rsplit("/", 1)[-1]
                if dev_id not in DEV_BY_ID:
                    self._send("<!doctype html><h1>Dispositivo no encontrado</h1><a href='/'>Volver</a>",
                               "text/html; charset=utf-8", 404)
                    return
                self._send(detail_page(DEV_BY_ID[dev_id]), "text/html; charset=utf-8")
            else:
                self.send_error(404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print("[DASH] error en %s: %s" % (path, e), flush=True)
            try:
                self._json({"ok": False, "message": str(e)}, 500)
            except Exception:
                pass

    def do_POST(self):
        path, q = self.path.split("?")[0], _qs(self.path)
        if path == "/api/dispatch":
            dev_id = q.get("dev") or None
            if dev_id and dev_id not in DEV_BY_ID:
                self._json({"ok": False, "message": "device no valido"}, 404)
                return
            out = dispatch_advisor(dev_id=dev_id)
            self._json(out, 200 if out.get("ok") or out.get("throttled") else 503)
            return
        self._json({"ok": False, "message": "ruta no valida"}, 404)

    def log_message(self, *args):
        pass


# ---------------------------------------------------------------- main
def selftest():
    assert current_extremes({"pm25": 912.0}) == ["pm25"]
    assert current_extremes({"pm25": 512.0}) == []
    assert current_extremes({"humidity": 3.0}) == ["humidity"]
    assert current_extremes({"flame": 1}) == ["flame"]
    assert current_extremes({"flame": 0}) == []
    pts = [{"t": "t%d" % i, "ts": float(i), "v": {"temperature": float(i)}} for i in range(100)]
    ds = downsample_minmax(pts, 10)
    assert len(ds) <= 12, len(ds)
    assert max(p["v"]["temperature"] for p in ds) == 99.0
    assert min(p["v"]["temperature"] for p in ds) == 0.0
    st = window_stats(pts)
    assert st["temperature"]["count"] == 100 and st["temperature"]["max"] == 99.0
    st2 = window_stats([{"t": "x", "ts": 1.0, "v": {"api_source": "open-meteo", "temperature": 21.0}}])
    assert st2["temperature"]["last"] == 21.0 and "api_source" not in st2
    _init_history()
    _buf["01"] = [{"t": "a", "ts": 0.0, "v": {}}, {"t": "b", "ts": 5000.0, "v": {}}]
    g = detect_gaps(DEV_BY_ID["01"])
    assert len(g) == 1 and g[0]["seconds"] == 5000.0, g
    _buf["01"] = []
    live = live_payload()
    assert len(live["devices"]) == 10
    hp = history_payload("01", range_key="24h", max_pts=50)
    assert hp["ok"] and "stats" in hp and "window" in hp
    name, csv, _n = export_csv("01", "all")
    assert csv.startswith("timestamp,")
    for fn, args in ((grid_page, ()), (evidencias_page, ()), (expand_page, (DEV_BY_ID["01"],))):
        html = fn(*args)
        assert "%HEADER%" not in html and "%EXTREMES%" not in html and "%UNITS%" not in html
        assert "<html" in html
    html = detail_page(DEV_BY_ID["01"])
    assert "%ID%" not in html and "%NAME%" not in html and "%ORIGIN%" not in html
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    if "--test-mail" in sys.argv:
        ok = send_brevo("Campus EMS — prueba de alertas",
                        "<p>Si recibes este correo, la pipeline de alertas por correo funciona.</p>")
        sys.exit(0 if ok else 1)
    _init_history()
    scan_once(force=True)
    threading.Thread(target=_loop, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print("[DASH] %s · servidor en http://0.0.0.0:%d · logs: %s · hist: %s"
          % (BASE, PORT, LOG_DIR, HISTORY_DIR), flush=True)
    server.serve_forever()
