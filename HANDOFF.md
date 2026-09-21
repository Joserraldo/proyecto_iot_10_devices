# HANDOFF — Estado tras despliegue en VM de José (2026-09-20)

**Fecha:** 2026-09-20
**Última actualización:** 2026-09-21
**Estado:** Flota completa 10/10 ✅ | Commit listo para push ✅ | Dashboard en puerto 8080 ✅

---

## Estado Actual

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
- **10/10 nodos corriendo y enviando telemetría** (D1–D10, verificado con logs 2026-09-21)
- Bridge D2 + ESP32 Wokwi funcionando (confirmado: `temp=26.7, hum=40.0, lux=19.9`)

**Dashboard local:** `http://57.156.66.112:8080` — sala de control completa con:
- Grid de 10 dispositivos (click abre detalle)
- Gráficos históricos Chart.js (1h/6h/24h/72h/all)
- KPIs con min/max por device
- Alertas por umbral + mail "Llamar asesor" (Brevo)

**Credenciales:** en `.env` local (gitignored) y en el `run_all_devices.sh` de la VM.
**NUNCA subirlas a GitHub.**

## Comandos útiles en la VM

```bash
ssh azureuser@57.156.66.112
bash ~/proyecto_iot_10_devices/status.sh            # procesos + logs
bash ~/proyecto_iot_10_devices/run_all_devices.sh   # lanzar flota
pkill -f 'sdk_node|api_node'                        # detener
tail -f ~/iotlogs/d2.log                            # ver D2 Wokwi
```

## Commit hecho (2026-09-21)

```bash
git push  # desde repo local
```

Commit `ad6dca4`:
- D2 Wokwi: sketch ESP32 con DHT22+LDR+LED, publicado en `campus/ems/D2`
- Bridge `mqtt_bridge_wokwi.py`: reenvía a IoT Central (ya corriendo en VM)
- `dashboard_server.py`: sala de control completa con gráficos históricos y alertas mail
- `run_dashboard_local.bat`: lanza dashboard en Windows
- Logs de depuración `[DX] TELE` en todos los scripts Python

## Lo que QUEDA PENDIENTE

1. **`git push`** — Commit `ad6dca4` hecho, solo falta subir a GitHub
2. **Capturar los 8 screenshots del portal** — guía en `evidencias/guia_screenshots_portal.md`
3. **D8**: repetir la desconexión controlada **en la app nueva** de José
   (`--disconnect-at 5`) y guardar evidencia con timestamps
4. **D6** (opcional): token WAQI gratuito para AQI real (hoy usa fallback)
5. **⚠️ Seguridad:** `run_all_devices.bat` (commit 4d0024c) tiene connection strings
   de la app de Buitrago hardcodeados — regenerar credenciales en la próxima release

## No tocar todavía
Dashboard Cuarto de Control de Azure, reglas de alerta de IoT Central, históricos CSV de 4 días, screenshots finales — fase siguiente del parcial.

## Notas técnicas

- Crear device templates vía API: raíz `@type: ["ModelDefinition","DeviceModel"]` + `@context`,
  capabilityModel `@type: "Interface"` sin `@id` por campo, path = DTMI del template.
- Token **Builder** puede crear templates; token admin da 500.
- Associar device a template: campo `templateId` (no `template`) con el DTMI del capability model.
- `mqtt_bridge_wokwi.py` compatible con paho 1.x y 2.x (try/except en `start_bridge`).
- Dashboard server: `python dashboard_server.py` → `http://0.0.0.0:8080`, lee logs de `~/iotlogs/`.