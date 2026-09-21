#!/usr/bin/env python3
"""
dashboard_server.py — Sala de control Campus EMS (10 dispositivos).

Sirve:
  GET  /                       → grid de toda la flota (click en tarjeta abre el detalle)
  GET  /device/{id}            → vista detalle: trackeo histórico completo tipo IoT Central
  GET  /api/status             → JSON de estado actual por device
  GET  /api/history?id=01[...] → JSON del histórico persistido (para las gráficas)
  POST /api/dispatch           → "Llamar asesor": mail de despacho con la ubicación
                                 de la alerta para que el asesor sepa a dónde ir.

- El histórico se acumula leyendo los logs ~/iotlogs/dX.log (líneas "[DX] TELE {...}")
  y se persiste en ~/iotlogs/history/dX.jsonl para sobrevivir reinicios de la flota.
- Alerta automática por mail (Brevo) solo cuando una lectura se mantiene en
  extremo durante MIN_EXTREME_S segundos seguidos, con re-notificación cada
  REALERT_S (anti-spam). El escaneo de logs y las alertas se pausan cuando no
  hay nadie mirando el dashboard (ACTIVE_WINDOW segundos sin requests).

Config: variables de entorno o archivo ../.env del repo:
  BREVO_API_KEY, BREVO_TO_EMAIL, BREVO_SENDER_EMAIL, ADVISOR_PHONE, DASH_PORT,
  LOG_DIR, HISTORY_DIR, REALERT_S, MIN_EXTREME_S, ACTIVE_WINDOW, HIST_MAX

Uso:
  python dashboard_server.py             # levanta el servidor (0.0.0.0:8080)
  python dashboard_server.py --test-mail # envía 1 mail de prueba y sale
  python dashboard_server.py --selftest  # corre checks de la lógica y sale
"""

import json
import os
import re
import sys
import time
import threading
import http.server

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
ADVISOR_PHONE = os.getenv("ADVISOR_PHONE") or _env.get("ADVISOR_PHONE", "+573000000000")
LOG_DIR = os.getenv("LOG_DIR") or os.path.expanduser("~/iotlogs")
HISTORY_DIR = os.getenv("HISTORY_DIR") or os.path.join(LOG_DIR, "history")
PORT = int(os.getenv("DASH_PORT", "8080"))
REALERT_S = int(os.getenv("REALERT_S", "21600"))          # re-notificar si sigue extremo (6 h)
MIN_EXTREME_S = int(os.getenv("MIN_EXTREME_S", "300"))    # extremo sostenido antes de alertar (5 min)
ACTIVE_WINDOW = int(os.getenv("ACTIVE_WINDOW", "300"))    # sin requests → pausar scan/alertas (5 min)
HIST_MAX = int(os.getenv("HIST_MAX", "30000"))            # máx puntos por device (aplanado)
CHART_MAX = int(os.getenv("CHART_MAX", "2000"))           # máx puntos por chart (downsampled)

# ---------------------------------------------------------------- catálogo
DEVICES = [
    {"id": "01", "name": "Estación meteo campus", "loc": "Campus", "interval": 15},
    {"id": "02", "name": "Meteo patio (Wokwi)", "loc": "Patio", "interval": 30},
    {"id": "03", "name": "Incendio Bloque A", "loc": "Bloque A", "interval": 60},
    {"id": "04", "name": "Incendio Laboratorio", "loc": "Laboratorio", "interval": 60},
    {"id": "05", "name": "Calidad aire aula", "loc": "Aula", "interval": 15},
    {"id": "06", "name": "Calidad aire exterior", "loc": "Exterior", "interval": 300},
    {"id": "07", "name": "Acceso principal", "loc": "Puerta principal", "interval": 30},
    {"id": "08", "name": "Cerramiento norte", "loc": "Perímetro norte", "interval": 60},
    {"id": "09", "name": "Evacuación pasillo", "loc": "Pasillo", "interval": 45},
    {"id": "10", "name": "Puesto de mando", "loc": "Centro de mando", "interval": 20},
]
DEV_BY_ID = {d["id"]: d for d in DEVICES}

# Extremos: (min, max); bounds=None = booleano donde 1/True es extremo.
# Rangos holgados: solo alertan condiciones realmente anómalas.
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
# campos a excluir del detalle y de las gráficas
SKIP_FIELDS = {"timestamp", "api_source", "source", "device_id", "csv_row", "mqtt_status", "ack_status", "emergency_status", "door_status", "motion", "ack_pending"}

TELE_RE = re.compile(r"\[D(\d{1,2})\] TELE (\{.*\})")

# ---------------------------------------------------------------- histórico
_history_file = {}
_buf = {}        # dev_id -> list of {"t": iso, "ts": float, "v": {...}}
_offsets = {}    # dev_id -> byte offset leído del log
_seen = {}       # dev_id -> set(md5 json) para dedup en truncación


def _dev_log(dev_id):
    return os.path.join(LOG_DIR, f"d{int(dev_id)}.log")


def _dev_hist(dev_id):
    return os.path.join(HISTORY_DIR, f"d{int(dev_id)}.jsonl")


def _init_history():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    for d in DEVICES:
        _buf[d["id"]] = []
        _offsets[d["id"]] = 0
        _seen[d["id"]] = set()
        path = _dev_hist(d["id"])
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        p = json.loads(line)
                        _buf[d["id"]].append(p)
                        _seen[d["id"]].add(p["t"])
                    except (json.JSONDecodeError, KeyError):
                        continue
        except OSError:
            pass
        _trim(d["id"])


def _trim(dev_id):
    buf = _buf[dev_id]
    if len(buf) > HIST_MAX:
        drop = buf[: len(buf) - HIST_MAX]
        _buf[dev_id] = buf[len(buf) - HIST_MAX:]
        _seen[dev_id] = {p["t"] for p in _buf[dev_id]}
        _persist(dev_id)
        return len(drop)
    return 0


def _persist(dev_id):
    try:
        with open(_dev_hist(dev_id), "w", encoding="utf-8") as f:
            for p in _buf[dev_id]:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"[HIST] {dev_id}: no se pudo persistir: {e}")


def _append(dev_id, p):
    _buf[dev_id].append(p)
    if len(_buf[dev_id]) % 40 == 0:
        _persist(dev_id)


def read_new(dev_id):
    """Lee líneas TELE nuevas del log (incremental por offset). Devuelve puntos."""
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
                ts = time.mktime(time.strptime(low[:19], "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, TypeError):
                ts = None
        now = time.time()
        item = {"t": raw or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
                "ts": ts or now, "v": v}
        _append(dev_id, item)


def read_latest(dev_id):
    """Última lectura del device (del buffer histórico)."""
    for p in reversed(_buf.get(dev_id, [])):
        return p["v"]
    return None


def device_points(dev_id, limit=None, after=None):
    pts = _buf.get(dev_id, [])
    if after is not None:
        pts = [p for p in pts if p["ts"] >= after]
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


# ---------------------------------------------------------------- mail (Brevo)
_alerts = {}   # {(dev, campo): {"was_extreme": bool, "last_sent": float}}


def send_brevo(subject, html):
    if not BREVO_API_KEY:
        print(f"[ALERT] BREVO_API_KEY no configurado — saltando correo: {subject}")
        return False
    if requests is None:
        print("[ALERT] requests no instalado — no se pudo enviar mail")
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
            headers={"api-key": BREVO_API_KEY, "accept": "application/json", "content-type": "application/json"},
            json=payload, timeout=20,
        )
    except Exception as e:
        print(f"[ALERT] Brevo error de red: {e}")
        return False
    if r.status_code not in (200, 201):
        print(f"[ALERT] Brevo {r.status_code}: {r.text[:300]}")
        return False
    print(f"[ALERT] Mail enviado: {subject}")
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
        # Debe llevar MIN_EXTREME_S seguidos en extremo para evitar picos sueltos.
        if (now - st["since"]) < MIN_EXTREME_S:
            _alerts[key] = st
            continue
        # Re-no alertar hasta REALERT_S después del último aviso del mismo campo.
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
            f"<p>El dispositivo <b>{dev['name']}</b> ({dev['loc']}) excedió el umbral extremo:</p><ul>{detalle}</ul>"
            f"<p>Fecha: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}</p>",
        )


_last_dispatch = [0.0]


def dispatch_advisor(dev_id=None):
    """'Llamar asesor' → mail de despacho con el lugar al que debe ir el asesor."""
    now = time.time()
    if now - _last_dispatch[0] < 15:
        return {"ok": True, "throttled": True, "message": "Despacho ya enviado hace instantes."}
    if dev_id:
        devs = [d for d in DEVICES if d["id"] == dev_id]
        context = [{"dev": d, "values": read_latest(dev_id) or {}} for d in devs]
    else:
        context = [{"dev": d, "values": read_latest(d["id"]) or {}} for d in DEVICES]
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
    _last_dispatch[0] = now
    ok = send_brevo("Campus EMS — Despacho de asesor: ubicación de la alerta", html)
    return {"ok": ok, "throttled": False, "message": "Mail de despacho enviado." if ok else "Fallo al enviar mail."}


# ---------------------------------------------------------------- estado
_last_scan = {"ts": 0}
_status = {}
_activity = {"ts": 0.0}   # última vez que alguien pidió datos al dashboard

def _touch_activity():
    _activity["ts"] = time.time()


def _recently_active():
    return (time.time() - _activity["ts"]) <= ACTIVE_WINDOW


def build_status():
    now = time.time()
    for dev in DEVICES:
        values = read_latest(dev["id"]) or {}
        _status[dev["id"]] = {
            **dev,
            "online": _online(dev, now),
            "values": values,
            "extremes": current_extremes(values),
            "points": len(_buf.get(dev["id"], [])),
        }
        if values:
            check_and_alert(dev, values, now)
    _last_scan["ts"] = now


def scan_once():
    for dev in DEVICES:
        try:
            read_new(dev["id"])
        except OSError as e:
            print(f"[SCAN] {dev['id']}: {e}")
    build_status()


def _loop():
    while True:
        try:
            if _recently_active():
                scan_once()
        except Exception as e:
            print(f"[DASH] error en scan: {e}", flush=True)
        time.sleep(15)


# ---------------------------------------------------------------- HTML (grid)
PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>Campus EMS — Sala de control</title>
<style>
  :root{
    --bg:#0b0f14;--bg2:#0e131a;--card:#141b24;--card2:#182130;--line:#26303e;--line2:#31414f;
    --txt:#e7eef6;--muted:#9fb0c3;--faint:#76909f;
    --ok:#3fb950;--off:#f85149;--warn:#d29922;--acc:#58a6ff;--okbg:#10301b;--offbg:#3a1a1a;--warnbg:#3a2a12;
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
         padding:14px 22px;background:rgba(11,15,20,.86);backdrop-filter:blur(8px);
         border-bottom:1px solid var(--line)}
  .brand{display:flex;align-items:center;gap:10px}
  .brand svg{display:block}
  h1{font-size:17px;margin:0;letter-spacing:.02em}
  h1 .sub{display:block;color:var(--faint);font-size:11px;font-weight:400;letter-spacing:.14em;text-transform:uppercase}
  .grow{flex:1}
  .sum{color:var(--muted);font-size:12px}
  #clock{color:var(--muted);font-size:12px;text-align:right}
  .btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:8px;cursor:pointer;
       font:600 13px/1 ui-monospace,Consolas,monospace;padding:9px 14px;transition:transform .12s ease,box-shadow .12s ease,filter .12s}
  .btn:hover{transform:translateY(-1px);filter:brightness(1.06)}
  .btn:active{transform:translateY(0)}
  .btn:disabled{opacity:.5;cursor:wait;transform:none}
  .btn-primary{background:var(--acc);color:#04121f}
  .btn-primary:not(:disabled){box-shadow:0 2px 14px rgba(88,166,255,.28)}
  .btn-ghost{background:var(--card2);color:var(--txt);border:1px solid var(--line2)}
  main{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;padding:20px 22px}
  .card{position:relative;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 15px;
        cursor:pointer;transition:border-color .15s,transform .15s,box-shadow .15s;
        animation:rise .4s cubic-bezier(.2,.7,.2,1) both}
  .card:nth-child(2){animation-delay:.03s}.card:nth-child(3){animation-delay:.06s}
  .card:nth-child(4){animation-delay:.09s}.card:nth-child(5){animation-delay:.12s}
  .card:nth-child(6){animation-delay:.15s}.card:nth-child(7){animation-delay:.18s}
  .card:nth-child(8){animation-delay:.21s}.card:nth-child(9){animation-delay:.24s}
  .card:nth-child(10){animation-delay:.27s}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .card:hover{border-color:var(--line2);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.35)}
  .card.warn{border-color:var(--warn)}
  .card.off{opacity:.78}
  .card .top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
  .name{font-weight:700;font-size:13px;letter-spacing:.01em}
  .loc{color:var(--muted);font-size:11px;margin-top:2px}
  .pill{font-size:10px;padding:3px 8px;border-radius:99px;font-weight:700;letter-spacing:.08em;white-space:nowrap}
  .pill.on{background:var(--okbg);color:var(--ok)}
  .pill.off{background:var(--offbg);color:var(--off)}
  .spark{margin:12px 0 10px;height:44px;display:block}
  .big{display:flex;align-items:baseline;gap:6px;font-size:11px;color:var(--faint)}
  .big b{color:var(--txt);font-size:22px;font-weight:700;font-variant-numeric:tabular-nums}
  .tags{margin-top:10px;display:flex;flex-wrap:wrap;gap:4px 12px;font-size:11px;color:var(--muted)}
  .tags span b{color:var(--txt);font-variant-numeric:tabular-nums}
  .badge{display:flex;align-items:center;gap:6px;color:var(--warn);font-size:11px;margin-top:10px}
  footer{color:var(--faint);font-size:11px;padding:12px 22px 30px}
  input[type=range]{accent-color:var(--acc)}
</style></head>
<body>
<header>
  <div class="brand" aria-hidden="true">
    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#58a6ff" stroke-width="1.6">
      <rect x="4" y="4" width="16" height="16" rx="3"/>
      <path d="M8 15l3-4 2 2 3-5"/>
    </svg>
  </div>
  <div class="grow">
    <h1>Campus EMS<span class="sub">Sala de control · 10 dispositivos</span></h1>
  </div>
  <div class="sum" id="sum">—</div>
  <button class="btn btn-primary" id="advisor" type="button">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2 4.2 2 2 0 0 1 4 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8 10a16 16 0 0 0 6 6l1.3-1.2a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z"/>
    </svg>
    Llamar asesor
  </button>
  <div id="clock">—</div>
</header>
<main id="grid"></main>
<footer id="foot">Cargando…</footer>
<script>
const e=document.getElementById('grid'),cl=document.getElementById('clock'),ft=document.getElementById('foot'),
      sum=document.getElementById('sum'),adv=document.getElementById('advisor');
function esc(s){return (s===null||s===undefined)?'':String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
const UNITS={'temperature':'°C','humidity':'%','pressure':'hPa','wind_speed':'m/s','wind_direction':'°','rainfall':'mm','lux':'lux','lux_nocturno':'lux','lux_emergency':'lux','pm25':'µg/m³','pm25_sim':'µg/m³','pm10_sim':'µg/m³','aqi':'AQI','co_level':'ppm','co2_sim':'ppm','no2_sim':'ppm','temperatura_promedio':'°C','sound_level':'dB','sound_alert':'dB','system_health':'%','occupancy':'pers','connected_devices':'disp'};
const LABELS={'temperature':'Temp','humidity':'Humedad','pressure':'Presión','wind_speed':'Viento','wind_direction':'Dir viento','rainfall':'Lluvia','lux':'Luz','lux_nocturno':'Luz noct','lux_emergency':'Luz emerg','pm25':'PM2.5','pm25_sim':'PM2.5','pm10_sim':'PM10','aqi':'AQI','co_level':'CO','co2_sim':'CO2','no2_sim':'NO2','smoke':'Humo','flame':'Llama','motion':'Mov','door_status':'Puerta','occupancy':'Ocupación','connected_devices':'Conectados','system_health':'Salud','temperatura_promedio':'Temp prom','sound_level':'Ruido','sound_alert':'Ruido'};
const SKIP=new Set(['timestamp','api_source','source','device_id','csv_row','mqtt_status','ack_status','emergency_status','door_status','motion','ack_pending','disconnected_devices']);
function fmtTime(ts){const t=new Date(ts*1000);return t.toLocaleTimeString('es-CO',{hour12:false});}
function num(k){return LABELS[k]&&!SKIP.has(k);}
function spark(canvas,pts,color,min,max){
  if(!pts.length||pts.length<2){return;}
  const dpr=window.devicePixelRatio||1,W=canvas.width/dpr,H=canvas.height/dpr;
  canvas.width=canvas.clientWidth*dpr;canvas.height=canvas.clientHeight*dpr;
  const g=canvas.getContext('2d');g.scale(dpr,dpr);
  const lo=(min===undefined)?Math.min(...pts):min,hi=(max===undefined)?Math.max(...pts):max,rn=(hi-lo)||1;
  g.clearRect(0,0,canvas.clientWidth,canvas.clientHeight);
  g.beginPath();
  pts.forEach((v,i)=>{const x=i/(pts.length-1)*canvas.clientWidth,y=canvas.clientHeight-4-((v-lo)/rn)*(canvas.clientHeight-8);i?g.lineTo(x,y):g.moveTo(x,y);});
  g.strokeStyle=color;g.lineWidth=1.6;g.lineJoin='round';g.stroke();
  g.strokeStyle=color;g.globalAlpha=.16;g.beginPath();
  g.moveTo(pts[0]===undefined?0:0,canvas.clientHeight-4);pts.forEach((v,i)=>{const x=i/(pts.length-1)*canvas.clientWidth,y=canvas.clientHeight-4-((v-lo)/rn)*(canvas.clientHeight-8);g.lineTo(x,y);});
  g.lineTo(canvas.clientWidth,canvas.clientHeight-4);g.closePath();g.fillStyle='rgba(0,0,0,0)';g.fill();
  g.globalAlpha=1;
}
function mainField(d){
  const keys=Object.keys(d.values||{});
  const pref=['temperature','pm25','aqi','co_level','temperature_promedio'];
  for(const p of pref){if(keys.includes(p))return p;}
  return keys.find(k=>num(k))||null;
}
const histCache={};
async function load(){
  try{
    const r=await fetch('/api/status');const j=await r.json();
    const devs=j.devices;
    const online=devs.filter(d=>d.online).length;
    sum.textContent=online+' de '+devs.length+' en línea';
    e.innerHTML=devs.map((d,ix)=>{
      const warn=d.extremes&&d.extremes.length;
      const mf=mainField(d);
      const withWarn=warn?' warn':'';
      const withOff=d.online?'':' off';
      let sparkHtml='';
      if(mf){
        const hist=(histCache[d.id]||{s:[]});
        const sr=[];
        for(let i=0;i<Math.min(hist.s.length||0,120);i++){sr.push(hist.s[i]);}
        sparkHtml='<canvas class="spark" data-d="'+d.id+'" data-f="'+mf+'"></canvas>';
      }
      const tags=Object.entries(d.values).filter(([k])=>num(k)).filter(([k])=>k===mf?false:true).slice(0,4)
        .map(([k,v])=>'<span>'+LABELS[k]+': <b>'+esc(v)+' '+esc(UNITS[k]||'')+'</b></span>').join('');
      const oddLabel=(warn&&d.values[d.extremes[0]]!==undefined)?d.extremes[0]:null;
      return `<article class="card${withWarn}${withOff}" tabindex="0" role="button" aria-label="Detalle de ${esc(d.name)}" onclick="location.href='/device/'+${JSON.stringify(d.id)}" onkeydown="if(event.key==='Enter')location.href='/device/'+${JSON.stringify(d.id)}">`
        +'<div class="top"><div><div class="name">'+d.id+' · '+esc(d.name)+'</div><div class="loc">'+esc(d.loc)+' · interv. '+d.interval+'s</div></div>'
        +'<span class="pill '+(d.online?'on':'off')+'">'+(d.online?'CONECTADO':'OFFLINE')+'</span></div>'
        +sparkHtml
        +('<div class="big"><b>'+(mf?esc(d.values[mf])+' '+esc(UNITS[mf]||''):'—')+'</b><span>'+(mf?LABELS[mf]:'sin telemetría')+'</span></div>')
        +(tags?'<div class="tags">'+tags+'</div>':'')
        +(warn?'<div class="badge">'+
          '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#d29922" stroke-width="2" aria-hidden="true"><path d="M12 3 2 20h20L12 3z"/><path d="M12 9v5"/><path d="M12 17.5v.5"/></svg>'
          +' Alerta: '+warn.map(k=>LABELS[k]||k).join(', ')+'</div>':'')
        +'</article>';
    }).join('');
    ft.textContent='Última lectura por device · '+new Date(j.now*1000).toLocaleTimeString('es-CO');
    cl.textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});
    afterPaint();
  }catch(err){
    e.innerHTML='<div class="card off"><div class="name">Sin conexión con el servidor</div></div>';
  }
}
function afterPaint(){
  const now=Date.now();
  document.querySelectorAll('canvas.spark').forEach(c=>{
    const id=c.dataset.d,f=c.dataset.f;
    const ci=histCache[id];
    if(ci&&ci.s&&ci.f===f&&now-(ci.at||0)<60000){spark(c,ci.s,ci.c);return;}
    fetch('/api/history?id='+id+'&limit=240').then(r=>r.json()).then(h=>{
      const pts0=h.points;
      let field=f||Object.keys(pts0[pts0.length-1]?.v||{}).find(k=>LABELS[k]&&!SKIP.has(k));
      if(!field)return;
      const pts=pts0.map(p=>p.v[field]).filter(v=>typeof v==='number');
      histCache[id]={s:pts,f:field,c:'#58a6ff',at:now};
      spark(c,pts,'#58a6ff');
    }).catch(()=>{});
  });
}
async function advisor(){
  adv.disabled=true;adv.lastCtx=null;
  const btn=adv;const old=btn.innerHTML;
  btn.innerHTML='<span class="spin" style="display:inline-block;animation:rise2 1s linear infinite">…</span> Enviando…';
  try{
    const r=await fetch('/api/dispatch',{method:'POST'});const j=await r.json();
    ft.textContent=j.message+' El correo indica al asesor a qué ubicación dirigirse.';
    if(j.throttled){ft.textContent=j.message;}
  }catch(err){ft.textContent='No se pudo enviar el despacho.';}
  setTimeout(()=>{btn.disabled=false;btn.innerHTML=old;},1500);
}
const spinStyle=document.createElement('style');spinStyle.textContent='@keyframes rise2{from{opacity:.2}to{opacity:1}}';document.head.appendChild(spinStyle);
adv.addEventListener('click',advisor);
function tick(){cl.textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});}
function whenVisible(fn,ms){
  const iv=setInterval(()=>{if(!document.hidden)fn();},ms);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)fn();});
}
whenVisible(load,15000);setInterval(tick,1000);
</script></body></html>"""


# ---------------------------------------------------------------- HTML (detalle)
DETAIL_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>%TITLE% — Campus EMS</title>
<style>
  :root{
    --bg:#0b0f14;--bg2:#0e131a;--card:#141b24;--card2:#182130;--line:#26303e;--line2:#31414f;
    --txt:#e7eef6;--muted:#9fb0c3;--faint:#76909f;
    --ok:#3fb950;--off:#f85149;--warn:#d29922;--acc:#58a6ff;
    --okbg:#10301b;--offbg:#3a1a1a;--warnbg:#3a2a12;
  }
  *{box-sizing:border-box}
  html{scrollbar-color:var(--line2) var(--bg)}
  body{margin:0;font-family:ui-monospace,'Cascadia Mono','Segoe UI Mono',Menlo,Consolas,monospace;
       background:radial-gradient(1200px 400px at 50% -80px,var(--bg2),var(--bg));color:var(--txt);min-height:100vh}
  ::selection{background:rgba(88,166,255,.32)}
  a{color:var(--acc);text-decoration:none}
  :focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:4px}
  header{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
         padding:13px 22px;background:rgba(11,15,20,.86);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
  .back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:12px;padding:6px 10px;border-radius:8px;border:1px solid var(--line)}
  .back:hover{color:var(--txt);border-color:var(--line2)}
  .ttl{min-width:0}
  h1{font-size:16px;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  h1 .id{color:var(--acc)}
  .loc{color:var(--muted);font-size:11px}
  .grow{flex:1}
  .pill{font-size:10px;padding:3px 8px;border-radius:99px;font-weight:700;letter-spacing:.08em}
  .pill.on{background:var(--okbg);color:var(--ok)}
  .pill.off{background:var(--offbg);color:var(--off)}
  #clock{color:var(--muted);font-size:12px}
  .btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:8px;cursor:pointer;
       font:600 13px/1 ui-monospace,Consolas,monospace;padding:9px 14px;transition:transform .12s,box-shadow .12s,filter .12s}
  .btn:hover{transform:translateY(-1px);filter:brightness(1.06)}
  .btn:disabled{opacity:.5;cursor:wait}
  .btn-primary{background:var(--acc);color:#04121f;box-shadow:0 2px 14px rgba(88,166,255,.28)}
  .btn-ghost{background:transparent;color:var(--muted);border:1px solid var(--line2)}
  .btn-alert{background:var(--off);color:#2a0505;box-shadow:0 2px 14px rgba(248,81,73,.35);animation:pulse 2s ease-out infinite}
  @keyframes pulse{0%,100%{box-shadow:0 2px 14px rgba(248,81,73,.35)}50%{box-shadow:0 4px 22px rgba(248,81,73,.6)}}
  .wrap{max-width:1180px;margin:0 auto;padding:20px 22px 60px}
  .alrt{display:none}
  .alrt.show{display:flex;gap:12px;align-items:flex-start;background:var(--offbg);border:1px solid var(--off);
             border-radius:12px;padding:14px 16px;margin-bottom:18px;animation:rise .3s cubic-bezier(.2,.7,.2,1) both}
  .alrt .tx{flex:1}
  .alrt h3{margin:0 0 4px;color:#ffb3ae;font-size:13px}
  .alrt p{margin:0;color:var(--txt);font-size:12px}
  #toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%);z-index:20;background:var(--card2);
         border:1px solid var(--line2);border-radius:10px;padding:10px 18px;font-size:12px;color:var(--txt);
         box-shadow:0 8px 30px rgba(0,0,0,.5);opacity:0;pointer-events:none;transition:opacity .25s}
  #toast.show{opacity:1}
  @keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:12px;margin-bottom:22px}
  .kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
  .kpi .k{color:var(--faint);font-size:10px;letter-spacing:.12em;text-transform:uppercase}
  .kpi .v{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums;margin:6px 0 2px}
  .kpi .u{font-size:12px;color:var(--muted)}
  .kpi .r{font-size:10px;color:var(--faint)}
  .panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:20px}
  .panel h2{margin:0 0 12px;font-size:12px;color:var(--muted);letter-spacing:.12em;text-transform:uppercase;font-weight:600}
  .toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
  .toolbar .seg{display:inline-flex;border:1px solid var(--line2);border-radius:8px;overflow:hidden}
  .toolbar .seg button{background:var(--card2);color:var(--muted);border:0;padding:7px 12px;font:600 11px/1 ui-monospace,Consolas,monospace;cursor:pointer}
  .toolbar .seg button.active{background:var(--acc);color:#04121f}
  .chartbox{position:relative;height:300px}
  .chartbox canvas{max-width:100%}
  table{width:100%;border-collapse:collapse;font-size:11.5px}
  th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--line);white-space:nowrap;font-variant-numeric:tabular-nums}
  th{color:var(--faint);font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:10px}
  th.stick{position:sticky;top:0;background:var(--card);z-index:1}
  td.ctl{color:var(--off)}
  .scroll{max-height:420px;overflow:auto}
  .foot{margin-top:26px;color:var(--faint);font-size:11px;text-align:center}
  .loadmore{display:inline-flex;align-items:center;gap:8px;margin-top:12px}
</style></head>
<body>
<div id="toast" role="status" aria-live="polite"></div>
<header>
  <a class="back" href="/">← Volver al mapa</a>
  <div class="ttl">
    <h1><span class="id">%ID%</span> · %NAME%</h1>
    <div class="loc">%LOC% · intervalo %INTERVAL%s</div>
  </div>
  <div class="grow"></div>
  <span class="pill" id="pill">…</span>
  <button class="btn btn-primary" id="adv" type="button">
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2 4.2 2 2 0 0 1 4 2h3a2 2 0 0 1 2 1.7c.1 1 .4 2 .7 2.9a2 2 0 0 1-.5 2.1L8 10a16 16 0 0 0 6 6l1.3-1.2a2 2 0 0 1 2.1-.5c.9.3 1.9.6 2.9.7a2 2 0 0 1 1.7 2z"/>
    </svg>
    <span id="advlbl">Llamar asesor</span>
  </button>
  <div id="clock">—</div>
</header>
<div class="wrap">
  <div class="alrt" id="alrt">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#f85149" stroke-width="2" aria-hidden="true" style="flex:none;margin-top:2px"><path d="M12 3 2 20h20L12 3z"/><path d="M12 9v5"/><path d="M12 17.5v.5"/></svg>
    <div class="tx">
      <h3>Lectura extrema detectada</h3>
      <p id="alrtmsg"></p>
    </div>
    <button class="btn btn-primary" id="adv2" type="button" style="flex:none">Enviar despacho</button>
  </div>
  <div class="kpis" id="kpis"></div>
  <div class="panel">
    <h2>Trackeo histórico · <span id="histlen">…</span> lecturas</h2>
    <div class="toolbar">
      <div class="seg" id="fields" role="group" aria-label="Métrica"></div>
      <div class="seg" id="ranges" role="group" aria-label="Rango de tiempo">
        <button type="button" data-r="1h">1h</button>
        <button type="button" data-r="6h">6h</button>
        <button type="button" data-r="24h">24h</button>
        <button type="button" data-r="72h">72h</button>
        <button type="button" data-r="all" class="active">todo</button>
      </div>
      <a class="btn btn-ghost" id="expand" href="/chart/%ID%" title="Abrir métrica ampliada con navegación en el tiempo">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></svg>
        Ampliar
      </a>
    </div>
    <div class="chartbox"><canvas id="chart" role="img" aria-label="Gráfica de la métrica seleccionada"></canvas></div>
  </div>
  <div class="panel">
    <h2>Registros</h2>
    <div class="scroll">
      <table><thead><tr><th class="stick">Hora</th><th class="stick">Lectura</th></tr></thead><tbody id="rows"></tbody></table>
    </div>
    <button class="btn btn-ghost loadmore" id="more" type="button">Cargar todo el histórico</button>
  </div>
  <div class="foot">Campus EMS · datos vía Azure IoT Central · actualización cada 15s</div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const EXTREMES=%EXTREMES%;
const ID='%ID%',DEV={id:ID,name:'%NAME%',loc:'%LOC%',interval:%INTERVAL%};
const $=id=>document.getElementById(id);
const UNITS={'temperature':'°C','humidity':'%','pressure':'hPa','wind_speed':'m/s','wind_direction':'°','rainfall':'mm','lux':'lux','lux_nocturno':'lux','lux_emergency':'lux','pm25':'µg/m³','pm25_sim':'µg/m³','pm10_sim':'µg/m³','aqi':'AQI','co_level':'ppm','co2_sim':'ppm','no2_sim':'ppm','temperatura_promedio':'°C','sound_level':'dB','sound_alert':'dB','system_health':'%','occupancy':'pers','connected_devices':'disp'};
const LABELS={'temperature':'Temp','humidity':'Humedad','pressure':'Presión','wind_speed':'Viento','wind_direction':'Dir viento','rainfall':'Lluvia','lux':'Luz','lux_nocturno':'Luz noct','lux_emergency':'Luz emerg','pm25':'PM2.5','pm25_sim':'PM2.5','pm10_sim':'PM10','aqi':'AQI','co_level':'CO','co2_sim':'CO2','no2_sim':'NO2','smoke':'Humo','flame':'Llama','temperatura_promedio':'Temp prom','sound_level':'Ruido','sound_alert':'Ruido','system_health':'Salud','occupancy':'Ocupación','connected_devices':'Conectados'};
const SKIP=new Set(['timestamp','api_source','source','device_id','csv_row','mqtt_status','ack_status','emergency_status','door_status','motion','ack_pending','disconnected_devices']);
let ALL=[],field=null,range='all',chart=null;
function esc(s){return (s===null||s===undefined)?'':String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function fmtT(ts){const t=new Date(ts*1000);return t.toLocaleString('es-CO',{hour12:false});}
function toast(m){const t=$('toast');t.textContent=m;t.classList.add('show');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('show'),3500);}
function numericFields(){if(!ALL.length)return[];const s=new Set();for(const p of ALL){for(const k in p.v){if(LABELS[k]&&!SKIP.has(k)&&typeof p.v[k]==='number')s.add(k);}}return [...s];}
function windowed(){
  if(range==='all')return ALL;
  const now=Date.now()/1000,sec={'1h':3600,'6h':21600,'24h':86400,'72h':259200}[range]||86400;
  return ALL.filter(p=>p.ts>=now-sec);
}
function downsample(pts,max){
  if(pts.length<=max)return pts;
  const step=pts.length/max,out=[];
  for(let i=0;i<max;i++)out.push(pts[Math.floor(i*step)]);
  return out;
}
function kpis(){
  const w=windowed();if(!w.length)return;
  const last=w[w.length-1].v;
  const el=$('kpis');el.innerHTML='';
  for(const [k,v] of Object.entries(last)){
    if(!LABELS[k]||SKIP.has(k))continue;
    const u=UNITS[k]||'';
    const vals=w.map(p=>p.v[k]).filter(x=>typeof x==='number');
    const mn=vals.length?Math.min(...vals):'—',mx=vals.length?Math.max(...vals):'—';
    const card=document.createElement('div');card.className='kpi';
    card.innerHTML='<div class="k">'+esc(LABELS[k])+'</div>'+
      '<div class="v">'+(typeof v==='number'?'<span class="dv" data-f="'+k+'"></span> ':esc(v))+'</div>'+
      '<div class="u">'+esc(u)+'</div><div class="r">min '+esc(mn)+' · máx '+esc(mx)+'</div>';
    el.appendChild(card);
  }
  document.querySelectorAll('.dv').forEach(n=>{animNum(n,last[n.dataset.f]);});
}
function animNum(node,val){
  const t0=performance.now(),dur=650,from=0;
  function step(t){const k=Math.min(1,(t-t0)/dur);const e=1-Math.pow(1-k,3);node.textContent=(from+(val-from)*e).toFixed(1);if(k<1)requestAnimationFrame(step);}
  requestAnimationFrame(step);
}
function draw(){
  if(!field||!window.Chart)return;
  const w=windowed(),pts=downsample(w,2000);
  const data=pts.map(p=>({x:p.ts*1000,y:p.v[field]})).filter(p=>typeof p.y==='number');
  if(!data.length)return;
  const okVals=data.map(d=>d.y);const lo=Math.min(...okVals),hi=Math.max(...okVals);const rn=(hi-lo)||1;const pad=rn*.12;
  const ctx=$('chart').getContext('2d');
  if(chart){chart.destroy();}
  const grad=ctx.createLinearGradient(0,0,0,300);
  grad.addColorStop(0,'rgba(88,166,255,.22)');grad.addColorStop(1,'rgba(88,166,255,0)');
  const datasets=[{data,label:LABELS[field],borderColor:'#58a6ff',backgroundColor:grad,fill:true,tension:.35,borderWidth:1.8,pointRadius:0,pointHitRadius:18}];
  const thr=EXTREMES[field];
  if(thr&&Array.isArray(thr)){
    const add=bd=>{const bound=bd===0?thr[0]:thr[1];if(bound===null)return;datasets.push({data:[{x:data[0].x,y:bound},{x:data[data.length-1].x,y:bound}],label:'umbral',borderColor:'#f85149',borderDash:[6,4],borderWidth:1.4,pointRadius:0,fill:false,tension:0});};
    add(0);add(1);
  }
  chart=new Chart(ctx,{
    type:'line',
    data:{datasets},
    options:{
      responsive:true,maintainAspectRatio:false,animation:{duration:500,easing:'easeOutQuart'},
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{display:false},
        tooltip:{backgroundColor:'#182130',borderColor:'#31414f',borderWidth:1,titleColor:'#9fb0c3',bodyColor:'#e7eef6',titleFont:{family:'ui-monospace,Consolas,monospace'},bodyFont:{family:'ui-monospace,Consolas,monospace'},displayColors:false}
      },
      scales:{
        x:{type:'linear',position:'bottom',ticks:{color:'#76909f',font:{family:'ui-monospace,Consolas,monospace',size:10},callback:v=>new Date(v).toLocaleTimeString('es-CO',{hour12:false})},grid:{color:'#1a2230'}},
        y:{suggestedMin:Math.max(0,lo-pad),suggestedMax:hi+pad,ticks:{color:'#76909f',font:{family:'ui-monospace,Consolas,monospace',size:10}},grid:{color:'#1a2230'}}
      }
    }
  });
}
function renderRows(){
  const tbody=$('rows');
  const cur=(range==='all')?ALL:windowed();
  const first=Math.max(0,cur.length-80);
  const slice=cur.slice(first);
  tbody.innerHTML=slice.slice().reverse().map(p=>{
    const kv=Object.entries(p.v).filter(([k])=>LABELS[k]&&!SKIP.has(k)).map(([k,v])=>LABELS[k]+'='+esc(v)).join('  ');
    return '<tr><td>'+fmtT(p.ts)+'</td><td>'+kv+'</td></tr>';
  }).join('');
}
function renderAllRows(){
  const tbody=$('rows');let acc='';
  for(let i=ALL.length-1;i>=0;i--){const p=ALL[i];const kv=Object.entries(p.v).filter(([k])=>LABELS[k]&&!SKIP.has(k)).map(([k,v])=>LABELS[k]+'='+esc(v)).join('  ');acc+='<tr><td>'+fmtT(p.ts)+'</td><td>'+kv+'</td></tr>';}
  tbody.innerHTML=acc;
}
async function loadAll(){
  const r=await fetch('/api/history?id='+ID+'&limit=0');
  ALL=(await r.json()).points;
  $('histlen').textContent=ALL.length;
  if(ALL.length){field=field||numericFields()[0];buildToggles();kpis();draw();renderRows();}
  updatePill();
}
function updatePill(){
  const d=(window._st&&window._st.devices||[]).find(x=>x.id===ID);
  const pill=$('pill');
  if(!d){pill.textContent='SIN DATOS';pill.className='pill off';return;}
  pill.textContent=d.online?'CONECTADO':'OFFLINE';pill.className='pill '+(d.online?'on':'off');
  const n=d.extremes.length;
  const alrt=$('alrt');const adv=$('adv'),adv2=$('adv2');
  if(n){
    alrt.classList.add('show');
    $('alrtmsg').textContent='En '+d.name+' ('+d.loc+'): '+d.extremes.map(k=>LABELS[k]||k).join(', ')+'. El asesor debe dirigirse a la ubicación señalada.';
    adv.classList.add('btn-alert');
  }else{alrt.classList.remove('show');adv.classList.remove('btn-alert');}
}
function buildToggles(){
  const seg=$('fields');seg.innerHTML='';
  numericFields().forEach(k=>{
    const b=document.createElement('button');b.type='button';b.textContent=LABELS[k];b.dataset.f=k;
    if(k===field)b.classList.add('active');
    b.addEventListener('click',()=>{field=k;seg.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x.dataset.f===k));draw();renderRows();});
    seg.appendChild(b);
  });
}
document.querySelectorAll('#ranges button').forEach(b=>{
  b.addEventListener('click',()=>{
    range=b.dataset.r;
    document.querySelectorAll('#ranges button').forEach(x=>x.classList.toggle('active',x.dataset.r===range));
    kpis();draw();renderRows();
  });
});
$('more').addEventListener('click',()=>{renderAllRows();toast('Histórico completo: '+ALL.length+' lecturas');$('more').textContent='Todo cargado ('+ALL.length+')';$('more').disabled=true;});
function advisor(alertMode){
  const btn=this||$('adv');btn.disabled=true;const old=btn.innerHTML;
  btn.innerHTML='Enviando…';
  fetch('/api/dispatch?dev='+ID,{method:'POST'})
    .then(r=>r.json()).then(j=>{
      toast(j.message);
      $('advlbl').textContent=j.ok||j.throttled?'Despacho enviado':'Error';
      setTimeout(()=>{btn.disabled=false;btn.innerHTML=old;$('advlbl').textContent='Llamar asesor';},1800);
    }).catch(()=>{toast('No se pudo enviar el despacho.');btn.disabled=false;btn.innerHTML=old;});
}
$('adv').addEventListener('click',()=>advisor.call($('adv'),false));
$('adv2').addEventListener('click',()=>advisor.call($('adv2'),true));
function whenVisible(fn,ms){
  const iv=setInterval(()=>{if(!document.hidden)fn();},ms);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)fn();});
}
(async()=>{
  await Promise.all([loadAll(),fetch('/api/status').then(r=>r.json()).then(j=>{window._st=j;updatePill();}).catch(()=>{})]);
  whenVisible(async()=>{
    try{const r=await fetch('/api/status');window._st=await r.json();updatePill();}catch(_){}
    cl.textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});
  },15000);
  setInterval(()=>{cl.textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});},1000);
})();
const cl=$('clock');
</script></body></html>"""

# ---------------------------------------------------------------- HTML (metric ampliada, tipo IoT Central)
EXPAND_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark">
<title>%TITLE% — Vista ampliada</title>
<style>
  :root{
    --bg:#0b0f14;--bg2:#0e131a;--card:#141b24;--card2:#182130;--line:#26303e;--line2:#31414f;
    --txt:#e7eef6;--muted:#9fb0c3;--faint:#76909f;--acc:#58a6ff;
    --ok:#3fb950;--off:#f85149;--warn:#d29922;
    --okbg:#10301b;--offbg:#3a1a1a;--warnbg:#3a2a12;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:ui-monospace,'Cascadia Mono','Segoe UI Mono',Menlo,Consolas,monospace;
       background:radial-gradient(1400px 500px at 50% -100px,var(--bg2),var(--bg));color:var(--txt);min-height:100vh}
  a{color:var(--acc);text-decoration:none}
  :focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:4px}
  header{position:sticky;top:0;z-index:10;display:flex;align-items:center;gap:12px;flex-wrap:wrap;
         padding:12px 22px;background:rgba(11,15,20,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
  .back{display:inline-flex;align-items:center;gap:6px;color:var(--muted);font-size:12px;padding:6px 10px;border-radius:8px;border:1px solid var(--line)}
  .back:hover{color:var(--txt);border-color:var(--line2)}
  .ttl{min-width:0}
  h1{font-size:15px;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  h1 .id{color:var(--acc)}
  .loc{color:var(--muted);font-size:11px}
  .grow{flex:1}
  #clock{color:var(--muted);font-size:12px}
  .wrap{height:calc(100vh - 58px);display:flex;flex-direction:column;max-width:1500px;margin:0 auto;padding:14px 22px 20px;width:100%}
  .toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
  .seg{display:inline-flex;border:1px solid var(--line2);border-radius:8px;overflow:hidden}
  .seg button{background:var(--card2);color:var(--muted);border:0;padding:7px 12px;font:600 11.5px/1 ui-monospace,Consolas,monospace;cursor:pointer}
  .seg button.active{background:var(--acc);color:#04121f}
  .seg button:disabled{opacity:.35;cursor:default}
  .segcl{display:inline-flex;align-items:center;gap:8px}
  .segcl input{background:var(--card2);color:var(--txt);border:1px solid var(--line2);border-radius:8px;padding:6px 10px;font:600 11.5px/1 ui-monospace,Consolas,monospace}
  .btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line2);background:var(--card2);color:var(--muted);
       border-radius:8px;cursor:pointer;font:600 12px/1 ui-monospace,Consolas,monospace;padding:7px 12px}
  .btn:hover{color:var(--txt);border-color:var(--acc)}
  .hint{color:var(--faint);font-size:11px;white-space:nowrap}
  .readout{font-size:11.5px;color:var(--acc);font-variant-numeric:tabular-nums;white-space:nowrap}
  .chartwrap{flex:1;position:relative;min-height:220px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px 8px}
  .chartwrap canvas{position:absolute;inset:0}
  .stats{display:flex;gap:20px;flex-wrap:wrap;margin-top:12px;font-size:12px;color:var(--muted);font-variant-numeric:tabular-nums}
  .stats b{color:var(--txt)}
  .pill{font-size:10px;padding:3px 8px;border-radius:99px;font-weight:700;letter-spacing:.08em;background:var(--okbg);color:var(--ok)}
  .pill.warn{background:var(--warnbg);color:var(--warn)}
  .pill.off{background:var(--offbg);color:var(--off)}
</style></head>
<body>
<header>
  <a class="back" href="/device/%ID%">← Detalle</a>
  <div class="ttl">
    <h1><span class="id">%ID%</span> · %NAME% · <span id="fld"></span></h1>
    <div class="loc">%LOC% · intervalo %INTERVAL%s</div>
  </div>
  <div class="grow"></div>
  <span class="readout" id="win">—</span>
  <div id="clock">—</div>
</header>
<div class="wrap">
  <div class="toolbar">
    <div class="seg" id="fields" role="group" aria-label="Métrica"></div>
    <div class="seg" id="ranges" role="group" aria-label="Ventana de tiempo">
      <button type="button" data-r="1h">1h</button>
      <button type="button" data-r="6h">6h</button>
      <button type="button" data-r="24h" class="active">24h</button>
      <button type="button" data-r="72h">72h</button>
      <button type="button" data-r="all">todo</button>
    </div>
    <div class="seg" id="nav" role="group" aria-label="Navegar en el tiempo">
      <button type="button" id="prev" title="Ventana anterior">◀</button>
      <button type="button" id="next" title="Ventana siguiente">▶</button>
      <button type="button" id="home" title="Volver a la ventana actual">●</button>
    </div>
    <div class="segcl">
      <input type="datetime-local" id="jump" aria-label="Ir a fecha y hora" title="Ir a ese momento (ventana centrada ahí)">
    </div>
    <span class="hint">Rueda: zoom · arrastre: mover en el tiempo</span>
  </div>
  <div class="chartwrap"><canvas id="chart" role="img" aria-label="Gráfica de la métrica ampliada"></canvas></div>
  <div class="stats">
    <span>último <b id="s_last">—</b></span>
    <span>min <b id="s_min">—</b></span>
    <span>pico <b id="s_pk">—</b></span>
    <span>prom <b id="s_avg">—</b></span>
    <span>lecturas <b id="s_n">—</b></span>
    <span>umbral <b id="s_thr">—</b></span>
  </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js"></script>
<script>
const EXTREMES=%EXTREMES%;
const ID='%ID%',DEV={id:ID,name:'%NAME%',loc:'%LOC%',interval:%INTERVAL%};
const $=id=>document.getElementById(id);
const UNITS={'temperature':'°C','humidity':'%','pressure':'hPa','wind_speed':'m/s','wind_direction':'°','rainfall':'mm','lux':'lux','lux_nocturno':'lux','lux_emergency':'lux','pm25':'µg/m³','pm25_sim':'µg/m³','pm10_sim':'µg/m³','aqi':'AQI','co_level':'ppm','co2_sim':'ppm','no2_sim':'ppm','temperatura_promedio':'°C','sound_level':'dB','sound_alert':'dB','system_health':'%','occupancy':'pers','connected_devices':'disp'};
const LABELS={'temperature':'Temp','humidity':'Humedad','pressure':'Presión','wind_speed':'Viento','wind_direction':'Dir viento','rainfall':'Lluvia','lux':'Luz','lux_nocturno':'Luz noct','lux_emergency':'Luz emerg','pm25':'PM2.5','pm25_sim':'PM2.5','pm10_sim':'PM10','aqi':'AQI','co_level':'CO','co2_sim':'CO2','no2_sim':'NO2','smoke':'Humo','flame':'Llama','temperatura_promedio':'Temp prom','sound_level':'Ruido','sound_alert':'Ruido','system_health':'Salud','occupancy':'Ocupación','connected_devices':'Conectados'};
const SKIP=new Set(['timestamp','api_source','source','device_id','csv_row','mqtt_status','ack_status','emergency_status','door_status','motion','ack_pending','disconnected_devices']);
let ALL=[],field=null,range='24h',chart=null;
function esc(s){return (s===null||s===undefined)?'':String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function fmtT(ts){const t=new Date(ts);return t.toLocaleString('es-CO',{hour12:false});}
function numericFields(){const s=new Set();for(const p of ALL){for(const k in p.v){if(LABELS[k]&&!SKIP.has(k)&&typeof p.v[k]==='number')s.add(k);}}return [...s];}
function downsample(pts,max){
  if(pts.length<=max)return pts;
  const step=pts.length/max,out=[];
  for(let i=0;i<max;i++)out.push(pts[Math.floor(i*step)]);
  return out;
}
function rangeBounds(){
  const ms=ALL.length?ALL[0].ts*1000:Date.now();
  const xs=ALL.map(p=>p.ts*1000);
  if(range==='all')return {lo:xs[0],hi:xs[xs.length-1]};
  const sec={'1h':3600,'6h':21600,'24h':86400,'72h':259200}[range]||86400;
  const hi=Date.now(),lo=hi-sec*1000;
  return {lo:lo,hi:hi};
}
function windowData(){
  const {lo,hi}=rangeBounds();
  const w=ALL.filter(p=>p.ts*1000>=lo&&p.ts*1000<=hi);
  return downsample(w,4000);
}
function setFieldHead(){
  $('fld').textContent=LABELS[field]||field;
  const thr=EXTREMES[field];$('s_thr').textContent=thr?thr.map(x=>x+' '+(UNITS[field]||'')).join('·'):'sin umbral';
  $('s_thr').style.color=thr?'var(--warn)':'var(--faint)';
}
function draw(){
  if(!field||!window.Chart)return;
  const data=windowData().map(p=>({x:p.ts*1000,y:p.v[field]})).filter(p=>typeof p.y==='number').sort((a,b)=>a.x-b.x);
  const ctx=$('chart').getContext('2d');
  if(chart){chart.destroy();}
  const xall=ALL.map(p=>p.ts*1000);
  const lim={lo:xall[0],hi:xall[xall.length-1]};
  const scale=ALL.length?{type:'time',bounds:'data',min:rangeBounds().lo,max:rangeBounds().hi,distribution:'linear',ticks:{maxTicksLimit:12,color:'#76909f',font:{size:11}},grid:{color:'#1c2532'}}:{};
  const datasets=data.length?[{data,label:LABELS[field],borderColor:'#58a6ff',backgroundColor:'rgba(88,166,255,.14)',fill:true,tension:.3,borderWidth:1.8,pointRadius:0,pointHitRadius:16}]:[];
  const thr=EXTREMES[field];
  if(thr&&thr[1]!=null&&data.length){datasets.push({label:'umbral máx',data:[{x:data[0].x,y:thr[1]},{x:data[data.length-1].x,y:thr[1]}],borderColor:'#f85149',borderDash:[5,4],borderWidth:1,pointRadius:0});}
  chart=new Chart(ctx,{
    type:'line',
    data:{datasets},
    options:{
      responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      animation:false,
      plugins:{
        zoom:{
          limits:{x:{min:lim.lo,max:lim.hi}},
          pan:{enabled:true,mode:'x',modifierKey:'shift',threshold:6},
          zoom:{wheel:{enabled:true,speed:.08,modifierKey:'ctrl'},drag:{enabled:false},pinch:{enabled:true},mode:'x'}
        },
        legend:{display:false},
        tooltip:{displayColors:false,titleFont:{size:12},bodyFont:{size:12},callbacks:{label:c=>c.dataset.label+': '+c.parsed.y+' '+(UNITS[field]||''),title:i=>i.length?fmtT(i[0].parsed.x):''}}
      },
      scales:{
        x:scale,
        y:{ticks:{color:'#76909f',font:{size:11},callback:v=>v+' '+(UNITS[field]||'')},grid:{color:'#1c2532'}}
      }
    }
  });
  chart.options.plugins.zoom.onZoom=chart.options.plugins.zoom.onPan=()=>updateReadout();
  stats();
}
function updateReadout(){
  if(!chart)return;
  const a=chart.scales.x;const t0=a.min!=null?a.min:rangeBounds().lo,t1=a.max!=null?a.max:rangeBounds().hi;
  $('win').textContent=fmtT(t0)+' → '+fmtT(t1);
}
function stats(){
  const w=windowData().map(p=>p.v[field]).filter(x=>typeof x==='number');
  if(!w.length){['last','min','pk','avg','n'].forEach(k=>$('s_'+k).textContent='—');return;}
  $('s_last').textContent=w[w.length-1],$('s_min').textContent=Math.min(...w),$('s_pk').textContent=Math.max(...w);
  $('s_avg').textContent=(w.reduce((a,b)=>a+b,0)/w.length).toFixed(1),$('s_n').textContent=w.length;
}
function rebuild(){
  document.querySelectorAll('#fields button').forEach(b=>b.classList.toggle('active',b.dataset.f===field));
  setFieldHead();draw();
}
function buildFields(){
  const seg=$('fields');seg.innerHTML='';
  numericFields().forEach(k=>{
    const b=document.createElement('button');b.type='button';b.textContent=LABELS[k];b.dataset.f=k;
    if(k===field)b.classList.add('active');
    b.addEventListener('click',()=>{field=k;rebuild();});
    seg.appendChild(b);
  });
  if(!field)field=document.querySelector('#fields button')?.dataset.f||null;
}
document.querySelectorAll('#ranges button').forEach(b=>{
  b.addEventListener('click',()=>{
    range=b.dataset.r;
    document.querySelectorAll('#ranges button').forEach(x=>x.classList.toggle('active',x.dataset.r===range));
    draw();
  });
});
function shift(backTo){
  if(!chart)return;
  const x=chart.scales.x,a=x.min!=null?x.min:rangeBounds().lo,b=x.max!=null?x.max:rangeBounds().hi;
  const span=b-a,stp=Math.max(span*.5,ALL.length>1?(ALL[1].ts-ALL[0].ts)*1000*4:3600e3);
  const lim=chart.options.plugins.zoom.limits.x;
  let lo=a+(backTo?-stp:stp),hi=b+(backTo?-stp:stp);
  if(lo<lim.min){lo=lim.min;hi=Math.min(lim.max,lo+span);}
  if(hi>lim.max){hi=lim.max;lo=Math.max(lim.min,hi-span);}
  x.min=lo;x.max=hi;chart.update('none');updateReadout();
}
$('prev').addEventListener('click',()=>shift(true));
$('next').addEventListener('click',()=>shift(false));
$('home').addEventListener('click',()=>{const d=rangeBounds();chart.scales.x.min=d.lo;chart.scales.x.max=d.hi;chart.update('none');updateReadout();});
$('jump').addEventListener('change',()=>{
  if(!chart||!$('jump').value)return;
  const t=new Date($('jump').value).getTime();
  const span=(chart.scales.x.max??rangeBounds().hi)-(chart.scales.x.min??rangeBounds().lo);
  const lim=chart.options.plugins.zoom.limits.x;
  const hi=Math.min(lim.max,t+span*.5),lo=Math.max(lim.min,hi-span);
  chart.scales.x.min=lo;chart.scales.x.max=hi;chart.update('none');updateReadout();
});
async function loadAll(){
  const r=await fetch('/api/history?id='+ID+'&limit=0');
  const j=await r.json();ALL=j.points||j||[];
  const limAll=ALL.map(p=>p.ts*1000);
  if(limAll.length)$('jump').min=new Date(limAll[0]).toISOString().slice(0,16);
}
(async()=>{
  const flds=document.createElement('button');flds.type='button';
  try{await loadAll();}catch(e){}
  buildFields();draw();
  setInterval(()=>{const cl=$('clock');cl.textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});},1000);
  $('clock').textContent=new Date().toLocaleTimeString('es-CO',{hour12:false});
  whenVisible(refreshLive,30000);
})();
async function refreshLive(){
  if(document.hidden)return;
  try{await loadAll();if(field)rebuild();}catch(_){}
}
function whenVisible(fn,ms){
  const iv=setInterval(()=>{if(!document.hidden)fn();},ms);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)fn();});
}
</script></body></html>"""

# umbrales expuestos al JS para pintado del tooltip/threshold
_EXTREMES_JS = json.dumps({k: list(v) if v else None for k, v in EXTREMES.items()}, ensure_ascii=False)
DETAIL_PAGE = DETAIL_PAGE.replace("%EXTREMES%", _EXTREMES_JS)
EXPAND_PAGE = EXPAND_PAGE.replace("%EXTREMES%", _EXTREMES_JS)

# ---------------------------------------------------------------- helpers de página
def fill_page(template, env):
    out = template
    for k, v in env.items():
        out = out.replace(k, v)
    return out


def detail_page(dev):
    env = {
        "%ID%": dev["id"],
        "%NAME%": dev["name"],
        "%LOC%": dev["loc"],
        "%INTERVAL%": str(dev["interval"]),
        "%TITLE%": dev["id"] + " — " + dev["name"],
    }
    return fill_page(DETAIL_PAGE, env)


def expand_page(dev):
    env = {
        "%ID%": dev["id"],
        "%NAME%": dev["name"],
        "%LOC%": dev["loc"],
        "%INTERVAL%": str(dev["interval"]),
        "%TITLE%": dev["id"] + " — " + dev["name"],
    }
    return fill_page(EXPAND_PAGE, env)


# ---------------------------------------------------------------- HTTP
class H(http.server.BaseHTTPRequestHandler):
    server_version = "CampusEMS/1.0"

    def _send(self, data, ctype):
        body = data.encode("utf-8") if isinstance(data, str) else data
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        q = {}
        for kv in self.path.split("?", 1)[-1].split("&"):
            if "=" in kv:
                k, _, v = kv.partition("=")
                q[k] = v
        if path == "/api/status":
            scan_once()
            _touch_activity()
            self._json({"now": _last_scan["ts"], "devices": [_status[k] for k in DEV_BY_ID if k in _status]})
        elif path == "/api/history":
            dev_id = q.get("id", "01")
            if dev_id not in DEV_BY_ID:
                self._json({"ok": False, "message": "device no válido"}, 404)
                return
            limit = 0 if q.get("limit") == "0" else max(1, int(q.get("limit", "200")))
            scan_once()
            _touch_activity()
            pts = device_points(dev_id, limit=limit)
            self._json({
                "ok": True, "id": dev_id, "name": DEV_BY_ID[dev_id]["name"],
                "loc": DEV_BY_ID[dev_id]["loc"], "points": pts,
            })
        elif path.startswith("/chart/"):
            dev_id = path.rsplit("/", 1)[-1]
            if dev_id not in DEV_BY_ID:
                self._send(("<h1 style='color:var(--txt)'>Dispositivo no encontrado · <a href='/'>← Inicio</a></h1>"), "text/html; charset=utf-8")
                return
            self._send(expand_page(DEV_BY_ID[dev_id]), "text/html; charset=utf-8")
        elif path.startswith("/device/"):
            dev_id = path.rsplit("/", 1)[-1]
            if dev_id not in DEV_BY_ID:
                self._send(("<!doctype html><html><body><h1>Dispositivo no encontrado</h1>"
                            "<a href='/'>← Volver</a></body></html>"), "text/html; charset=utf-8")
                return
            self._send(detail_page(DEV_BY_ID[dev_id]), "text/html; charset=utf-8")
        elif path == "/":
            self._send(fill_page(PAGE, {"ADVISOR_PHONE": ADVISOR_PHONE}), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def do_POST(self):
        path = self.path.split("?")[0]
        q = {}
        for kv in self.path.split("?", 1)[-1].split("&"):
            if "=" in kv:
                k, _, v = kv.partition("=")
                q[k] = v
        if path == "/api/dispatch":
            dev_id = q.get("dev") or None
            if dev_id and dev_id not in DEV_BY_ID:
                self._json({"ok": False, "message": "device no válido"}, 404)
                return
            out = dispatch_advisor(dev_id=dev_id)
            self._json(out, 200 if out.get("ok") or out.get("throttled") else 503)
            return
        self._json({"ok": False, "message": "ruta no válida"}, 404)

    def log_message(self, *args):
        pass


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        assert current_extremes({"pm25": 912.0}) == ["pm25"]
        assert current_extremes({"pm25": 512.0}) == []
        assert current_extremes({"humidity": 3.0}) == ["humidity"]
        assert current_extremes({"flame": 1}) == ["flame"]
        assert current_extremes({"flame": 0}) == []
        _init_history()
        assert "01" in _buf and isinstance(_buf["01"], list)
        pts = device_points("01", limit=10)
        assert isinstance(pts, list) and all("v" in p and "ts" in p for p in pts)
        print("selftest OK")
        sys.exit(0)
    if "--test-mail" in sys.argv:
        ok = send_brevo("Campus EMS — prueba de alertas",
                        "<p>Si recibes este correo, la pipeline de alertas por correo funciona.</p>")
        sys.exit(0 if ok else 1)
    _init_history()
    scan_once()
    threading.Thread(target=_loop, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"[DASH] {BASE} · servidor en http://0.0.0.0:{PORT} · logs: {LOG_DIR} · hist: {HISTORY_DIR}", flush=True)
    server.serve_forever()