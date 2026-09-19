# Azure IoT Central - Parcial 1: Flota Heterogénea de 10 Dispositivos

**Curso:** IoT + Cloud + Sistemas Distribuidos (UNAB)  
**Autores:** José Alejandro Téllez Prada y Juan Sebastian Buitrago Caballero  
**Semestre:** 6°  
**Fecha:** 2026-09-18

## 📋 Descripción General

Este proyecto implementa un escenario de Azure IoT Central con una flota heterogénea de 10 dispositivos, cubriendo el escenario de **Gestión de Emergencias en Campus Universitario**. El objetivo es diseñar, configurar, simular y documentar un sistema IoT completo con telemetría histórica y en vivo, asincronía, desconexiones controladas y un dashboard tipo "Cuarto de Control".

## 🎯 Escenario Seleccionado

**Opción 3.4: Campus Colegio Caldas / Universidad UNAB - Gestión de Emergencias**

El escenario cubre monitoreo meteorológico, detección de incendios, calidad de aire, gestión de accesos y coordinación de evacuaciones en un campus universitario.

## 📡 Arquitectura de 4 Capas

1. **Capa Dispositivo:** 10 nodosheterogéneos con orígenes de datos distintos (Digital Twin, Wokwi, Python SDK, APIs públicas, Atlas Weather, CSV replay)
2. **Capa Telecomunicaciones:** MQTT/TLS, HTTPS, protocolos variados con intervalos de muestreo asíncronos (15s, 30s, 60s, 5min)
3. **Capa Plataforma:** Azure IoT Central con Device Templates, DPS (Device Provisioning Service), reglas de alerta y dashboards
4. **Capa Operación:** Views, dashboards personalizados, KPIs, mapa de distribución, gestión de alarmas

## 📦 Dispositivos (10 Nodos)

| ID | Dispositivo | Zona | Origen | Protocolo | Intervalo |
|---|---|---|---|---|---|
| D1 | Estación meteo campus | Área central | Digital Twin | MQTT/TLS | 15 s |
| D2 | Meteo patio / cubierta | Patio | Wokwi | MQTT | 30 s |
| D3 | Incendio Bloque A | Bloque A | Python SDK | MQTT/TLS | 60 s |
| D4 | Incendio Laboratorio | Laboratorio | Python SDK | MQTT/TLS | 1 min |
| D5 | Calidad aire aula | Aula | API Pública | HTTPS | 15 s |
| D6 | Calidad aire exterior | Exterior | Atlas Weather | HTTPS | 5 min |
| D7 | Acceso principal | Entrada | MQTT Explicito | MQTT | 30 s |
| D8 | Cerramiento norte | Perímetro | Replay CSV | Local | 1 min |
| D9 | Evacuación pasillo | Pasillo | Digital Twin | MQTT/TLS | 45 s |
| D10 | Puesto de mando | Mando | Digital Twin | MQTT/TLS | 20 s |

## 🚀 Primeros Pasos

1. **Seleccionar escenario:** Opción 3.4 definida
2. **Configurar Device Template:** En Azure IoT Central
3. **Ejecutar nodos:** Python en VM de Azure, Wokwi local
4. **Ver dashboard:** Cuarto de Control personalizado

## 📁 Estructura del Repositorio

```
.
├── .gitignore              # Configuración git
├── TODO.md                 # Bitácora de tareas
├── .opencode/              # Contexto y planificación
│   ├── todo.md             # Misión completa
│   ├── context.md          # Contexto del proyecto
│   └── work-log.md         # Registro de trabajo
├── python/                 # Nodos y scripts Python
│   ├── sdk_conexion.py     # Conexión SDK Azure IoT
│   └── nodos/              # Scripts por dispositivo
├── wokwi/                  # Diagramas y configuración Wokwi
├── docs/                   # Documentación técnica
├── evidencias/           # Capturas, logs y pruebas
├── tools/                  # Herramientas auxiliares
└── requirements.txt        # Dependencias Python
```

---

## 🔄 Cambios Juan — 2026-09-19

### ✅ Fase 1 — Código (completa)
- Corregidos todos los bugs críticos en los 11 scripts Python y el sketch ESP32 (D2)
- D1: SyntaxError fatal corregido
- D3: `main()` no hacía nada — reescrito completo
- D4: `handle_command` usaba API incorrecta del SDK — corregido
- D5: API falsa reemplazada con Open-Meteo real; CO2/PM etiquetados como simulados
- D6: URL Atlas Weather no existe — reemplazada con WAQI
- D7: imports faltantes, broker MQTT incorrecto, `CallbackAPIVersion` incompatible con paho 1.6 — corregido
- D8: bug en `timedelta` corregido
- D9: `random.choices()` sin argumento obligatorio — corregido
- D10: JSON anidado aplanado a escalares para IoT Central
- Bridge D2: `SyntaxError` en asignación — corregido
- Sketch Wokwi D2: sin WiFi.begin ni MQTT publish — reescrito completo

### ✅ Fase 2 — Azure IoT Central (completa)

**Infraestructura creada:**
- App `campus-ems` en Azure IoT Central (`campus-ems.azureiotcentral.com`)
- Device Template `campus-emergency-v1` publicado con 34 campos de telemetría
- 10 dispositivos registrados (`campus-ems-01` al `campus-ems-10`)
- Provisioning via DPS completado — connection strings generados con `python/provision_devices.py`

**Telemetría verificada en Azure — 2026-09-19:**

| Device | Estado | Telemetría | Intervalo |
|---|---|---|---|
| D1 Estación meteo campus | ✅ Conectado | ✅ temp, humidity, pressure, wind, rainfall | 15 s |
| D2 Meteo patio Wokwi | ⏳ Pendiente | — | 30 s |
| D3 Incendio Bloque A | ✅ Conectado | ✅ temp, smoke, flame, co_level | 60 s |
| D4 Incendio Laboratorio | ✅ Conectado | ✅ temp, smoke, flame, co_level, door_status | 60 s |
| D5 Calidad aire aula | ✅ Conectado | ✅ temp/hum/wind (Open-Meteo real) + co2_sim, pm25_sim, pm10_sim | 15 s |
| D6 Calidad aire exterior | ✅ Conectado | ✅ temp, aqi, pm25, pm10 (fallback Open-Meteo) | 300 s |
| D7 Acceso principal | ✅ Conectado | ✅ door_status, occupancy, temperature | 30 s |
| D8 Cerramiento norte | ✅ Conectado | ✅ motion, lux_nocturno, temperature (CSV real) | 60 s |
| D9 Evacuación pasillo | ✅ Conectado | ✅ occupancy, lux_emergency, emergency_status | 45 s |
| D10 Puesto de mando | ✅ Conectado | ✅ connected_devices, system_health, ack_status | 20 s |

### ⏳ Lo que falta

- **D2**: probar flujo completo Wokwi → MQTT → bridge → Azure
- **D8**: demostrar desconexión/reconexión con `--send-to-cloud --disconnect-at N` en Azure
- **D6**: registrar token WAQI para datos reales de calidad de aire (actualmente usa fallback)

### ❌ No tocar todavía
Dashboard, reglas de alerta, históricos CSV de 4 días, screenshots finales.

---

## ⚠️ Consideraciones de Seguridad

- **NUNCA** almacenar credenciales, connection strings ni secretos en el repositorio
- Todas las credenciales deben venir de **variables de entorno** (` .env `)
- Usar **DPS** (Device Provisioning Service) para el registro de dispositivos
- `.env` y `.env.example` están en `.gitignore`

## 📚 Referencias

- Guía Técnica Parcial: `Guia_tecnica_parcial.md`
- Trabajos Previos: `D:\José Tellez\Documents\universidad\sexto semestre\Iot_learning` o `https://github.com/Joserraldo/Iot_learning`
- Prompt Maestro: Véase `TODO.md` línea 198-253