# HANDOFF - Primer Avance Parcial 1 IoT

**Fecha:** 2026-09-19
**Autor del handoff:** José Tellez
**Continúa mañana:** Colega del equipo (Buitrago)

---

## Estado Actual (Todo CÓDIGO EN DISCO ✅)

Todo el código fuente existe en el repo con rutas correctas. Nada está vacío.

| Carpeta | Contenido | Estado |
|---|---|---|
| `python/` | 11 scripts (10 nodos + simulador local) | ✅ |
| `wokwi/` | 1 diagrama ESP32 (D2) | ✅ |
| `data/` | 1 CSV replay de 4 días (D8) | ✅ |
| `docs/` | 7 documentos técnicos | ✅ |
| `evidence/` | vacía a propósito (gitignore) | ⬜ |

## Cómo probar AHORA sin Azure

Toda la flota funciona en **modo local sin credenciales**:

```bash
cd python
# Probar un nodo individual (telemetria JSON en consola)
python device_simulator_local.py --type estacion_meteo --interval 15
python device_simulator_local.py --type incendio --interval 60
python device_simulator_local.py --type acceso --interval 30

# Probar desconexion controlada (D8 - Replay CSV)
python sdk_node_d8.py --disconnect-at 5
```

Los SDK nodes (`sdk_node_dX.py`) hacen **fallback al simulador local** si no hay `AZURE_CONNECTION_STRING`, así que corren sin Azure.

## Dispositivos e intervalos (asincronía)

| Nodo | Zona | Origen | Intervalo |
|---|---|---|---|
| D1 | Estación meteo | SDK + sim | 15 s |
| D2 | Meteo patio | Wokwi ESP32 | 30 s |
| D3 | Incendio Bloque A | SDK | 20 s |
| D4 | Incendio Lab | SDK (writable+cmd) | 30 s |
| D5 | Calidad aire aula | Open-Meteo API | 45 s |
| D6 | Calidad exterior | WAQI/Atlas API | 300 s |
| D7 | Acceso principal | SDK MQTT | 15 s |
| D8 | Cerramiento norte | Replay CSV | 60 s |
| D9 | Evacuación pasillo | SDK | 20 s |
| D10 | Puesto de mando | HTTP bridge | 30 s |

## Lo que QUEDÓ PENDIENTE (para mañana)

1. **Credenciales Azure IoT Central**: completar `.env` real (copiar `.env.example`, llenar `AZURE_CONNECTION_STRING` de cada device o DPS).
2. **Crear Device Template** `campus-emergency-v1` en Azure IoT Central (ver `docs/device-template.md`).
3. **Probar conexión real**: con credenciales, los SDK nodes envían a Central.
4. **Dashboard Cuarto de Control** en IoT Central (ver `docs/control-room.md`).
5. **Capturas de evidencia** para la sustentación (guardar en `evidencias/`).

## Advertencia (bug corregido)

Los archivos inicialmente se escribieron con rutas estilo Unix (`/d/...`) que no persistían en Windows.
**Se reescribieron todos con rutas Windows (`D:\...`) y verificados en disco con `ls -la`.**
Si algún archivo parece faltar, revisar que el path del repo sea:
`D:\José Tellez\Documents\universidad\sexto semestre\proyecto_iot_10_devices`

## ADVERTENCIA Git

`.gitignore` excluye `*.env*` — **`.env.example` no se trackea**. Para subirlo, forzar con `git add -f .env.example` o ajustar el gitignore. El `.env` real NO se sube jamás.