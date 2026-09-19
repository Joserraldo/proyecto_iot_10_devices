# Evidencia - Desconexión Controlada D8 (Cerramiento norte)

**Fecha:** 2026-09-19
**Script:** `python/sdk_node_d8.py --disconnect-at 2 --iterations 6`
**Intervalo configurado:** D8_INTERVAL=3s (prueba rápida local; en producción 60s)
**Modo:** local (sin Azure) — valida el procedimiento de desconexión/reconexión

## Timestamps capturados

| Evento | Iteración | Timestamp (UTC) | Hora local |
|---|---|---|---|
| Última telemetría antes de desconexión | 1 | — | 01:14:42.607 |
| **DESCONEXIÓN CONTROLADA** | 2 | 2026-09-19T06:14:45.607386+00:00 | 01:14:45.607 |
| **RECONEXIÓN** | 2 | 2026-09-19T06:14:51.607785+00:00 | 01:14:51.607 |
| Primera telemetría tras reconexión | 3 | — | 01:14:51.607 |

**Hueco de datos:** ~6.0 segundos sin telemetría (intervalo × 2, conforme al diseño)

## Observaciones

- El nodo detuvo el envío de telemetría en la iteración 2 (bandera `--disconnect-at 2`).
- La reconexión fue automática al expirar la ventana de desconexión (2 intervalos).
- La telemetría se reanudó sin intervención manual ni pérdida de estado.
- En Azure IoT Central, este hueco se observará como gap en el gráfico de telemetría
  y el estado del device pasará a etapa de desconexión similar si se corta el transporte.

## Procedimiento en producción (Azure)

```bash
# 1. Iniciar D8 con telemetría real hacia IoT Central
python sdk_node_d8.py --send-to-cloud

# 2. Detener el proceso (Ctrl+C) => IoT Central marca el device como desconectado
# 3. Capturar timestamp local del corte
# 4. Capturar screenshot del dashboard mostrando el gap
# 5. Reiniciar el proceso => reconexión automática vía DPS/SDK
python sdk_node_d8.py --send-to-cloud
```

## Reproducir la evidencia local

```bash
cd python
D8_INTERVAL=3 python sdk_node_d8.py --disconnect-at 2 --iterations 6
```