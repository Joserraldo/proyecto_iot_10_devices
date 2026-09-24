# Rules de alerta — Azure IoT Central (a crear en el portal)

> Las Rules NO se pueden crear por REST API (no están expuestas). Se crean en el
> portal: menú **Rules** → **New rule**. Después de guardar, quedan activas y
> disparan email/webhook cuando la telemetría cruza el umbral. El correo debe ser
> un usuario de la app que haya iniciado sesión al menos una vez.

Configuración común a todas:

- **Device template:** `campus-emergency-v1` (cubre toda la flota por el device group default).
- **Target:** `campus-emergency-v1 - All devices` (creado automático).
- **Action:** Email `jose.tellez@...` + notas con dispositivo/zona (opcional webhook).
- **Severity:** High / Critical según tipo.

## Rule 1 — FUEGO: humo detectado (Critical)
Condición: `smoke` **is true** (telemetry, sin agregación).
Justificación: humo = incendio activo, respuesta inmediata.

## Rule 2 — FUEGO: llama detectada (Critical)
Condición: `flame` **is true**.

## Rule 3 — FUEGO: monóxido alto (High)
Condición: `co_level` **is greater than** `600` ppm.
> Umbral alto = exposición humana peligrosa (datasheet MQ-7: detección 20–2000 ppm).

## Rule 4 — INCENDIO: temperatura de techo extrema (Critical)
Condición: `temperature` **is greater than** `65` °C.
> Techo normal <40 °C; >65 °C = fuego declarado (nodos D3/D4).

## Rule 5 — CALIDAD DE AIRE: AQI extremo (High)
Condición: `aqi` **is greater than** `350`.
> Nivel >300 = "Peligroso" (EPA). Nodo D6.

## Rule 6 — CALIDAD DE AIRE: PM2.5 extremo (High)
Condición: `pm25` **is greater than** `500` µg/m³.
> Índice "Hazardous" EPA. Nodo D5/D6.

## Rule 7 — METEO: humedad peligrosa (Medium)
Condición: `humidity` **is less than** `5` % **OR** `humidity` **is greater than** `98` %.
> Saturación/inundación o sequía extrema (nodos D1/D2/D5).

## Evidencia que capturar (portal → Rules)
1. Pantalla **Rules** con las 7 reglas y toggle Enabled ON.
2. Abrir una regla (ej. FUEGO humo) mostrando condición + acción email.
3. (Opcional) Email recibido si un umbral se cruza.