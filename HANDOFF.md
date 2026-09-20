# HANDOFF — Estado tras despliegue en VM de José (2026-09-20)

**Fecha:** 2026-09-20
**Continúa mañana:** José (commit pendiente + evidencias de portal)

---

## Estado Actual (DESPLIEGUE COMPLETO ✅)

**App IoT Central de José** (nueva, estaba vacía) — todo creado el 2026-09-20 vía REST API:

| Recurso | Valor |
|---|---|
| ID Scope | `0ne012B4879` |
| IoT Hub | `iotc-371f401d-4819-4938-ad41-996a5a907560.azure-devices.net` |
| Device Template | `campus-emergency-v1` — 35 campos, creado vía API con token Builder |
| Devices | `campus-ems-01`…`10` — 10/10 **Provisioned** |

**VM Azure** (`vm-parcial-jose-juancho`, 57.156.66.112, Ubuntu 24.04):
- Repo en `~/proyecto_iot_10_devices` + venv con dependencias
- `run_all_devices.sh` lanza la flota en background — logs en `~/iotlogs/`
- **9/10 nodos corriendo y enviando telemetría** (D1, D3–D10, verificado con logs)
- Bridge D2 corriendo, suscrito a `campus/ems/D2` en test.mosquitto.org, esperando al ESP32 de Wokwi

**Credenciales:** en `.env` local (gitignored) y en el `run_all_devices.sh` de la VM.
**NUNCA subirlas a GitHub.**

## Comandos útiles en la VM

```bash
ssh azureuser@57.156.66.112
bash ~/proyecto_iot_10_devices/status.sh            # procesos + logs
bash ~/proyecto_iot_10_devices/run_all_devices.sh   # lanzar flota
pkill -f 'sdk_node|api_node'                        # detener
tail -f ~/iotlogs/d2.log                            # ver bridge D2
```

## Lo que QUEDA PENDIENTE (para mañana)

1. **Commit** de los cambios locales (ver mensaje abajo): README, TODO, fix bridge.
2. **Capturar los 8 screenshots del portal** — guía paso a paso en
   `evidencias/guia_screenshots_portal.md`. La flota debe estar corriendo
   (verificar con `status.sh`; si la VM se reinició, relanzar con `run_all_devices.sh`).
3. **D2 — cerrar flujo Wokwi**: pegar el sketch en wokwi.com (extraer con
   `python -c "import json; print(json.load(open('wokwi/d2_esp32_meteo_patio.json',encoding='utf-8'))['sketch'])"`),
   dar Play, y verificar en la VM `tail -f ~/iotlogs/d2.log` →
   `[BRIDGE-D2] Reenviado a IoT Central`. El bridge ya está suscrito a `campus/ems/D2`.
4. **D8**: repetir la desconexión controlada **en la app nueva** de José
   (`--disconnect-at 5`) y guardar evidencia con timestamps (la actual es de la app de Buitrago).
5. **D6** (opcional): token WAQI gratuito para AQI real (hoy usa fallback).
6. **⚠️ Seguridad antes de publicar en GitHub:** `run_all_devices.bat` tiene los
   connection strings de la app de Buitrago hardcodeados (commit 4d0024c). Removerlos
   y moverlos a variables de entorno o fuera del repo.

## No tocar todavía
Dashboard Cuarto de Control, reglas de alerta, históricos CSV de 4 días, screenshots finales — fase siguiente del parcial.

## Notas técnicas útiles

- Crear device templates vía API requiere el formato exacto:
  raíz `@type: ["ModelDefinition","DeviceModel"]` + `@context` en la raíz,
  capabilityModel `@type: "Interface"` sin `@id` por campo, path = DTMI del template.
  El token **Builder** puede crear templates; el token admin da 500.
- Asociar device a template: campo `templateId` (no `template`) con el DTMI del
  capability model.
- Credenciales por device: `GET /devices/{id}/credentials` → idScope + primaryKey.
- Los scripts Python leen variables de entorno con `os.getenv()` (no cargan `.env`):
  el `run_all_devices.sh` exporta el connection string correcto por proceso.
- `mqtt_bridge_wokwi.py` quedó compatible con paho 1.x y 2.x (try/except en `start_bridge`).
