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

### ✅ Lo que quedó listo

**Código — Fase 1 completa**
- Corregidos todos los bugs críticos en los 11 scripts Python y el sketch ESP32 (D2)
- D1: SyntaxError fatal corregido — ya conecta y envía telemetría
- D3: `main()` no hacía nada — reescrito completo para que conecte y envíe
- D4: comandos remotos (`handle_command`) usaban API incorrecta del SDK — corregido
- D5: reemplazada API falsa — ahora usa Open-Meteo real para temperatura/humedad/viento; CO2 y PM etiquetados como simulados
- D6: URL de Atlas Weather no existe — reemplazada con WAQI (calidad de aire real gratuita)
- D7: imports faltantes, broker MQTT incorrecto — corregido
- D8: bug en `timedelta`, desconexión/reconexión verificada con timestamps reales
- D9: `random.choices()` sin argumento obligatorio — corregía con TypeError en cada ciclo
- D10: JSON anidado aplanado a campos escalares (IoT Central no grafica objetos anidados)
- Bridge D2: `SyntaxError` en asignación — bridge nunca arrancaba
- Sketch Wokwi D2: no tenía WiFi.begin ni MQTT publish — reescrito completo

**Preparación Azure — Fase 2**
- `iotcentral/device_template_campus_emergency_v1.json` — plantilla DTDL con los 34 campos reales de los 10 dispositivos, lista para importar directo en IoT Central
- `.env.example` — reescrito con las variables reales que lee cada script (D3 tiene nombre de variable distinto, documentado)
- `python/provision_devices.py` — script que obtiene los connection strings de Azure via DPS; solo necesita ID Scope + Master Key

### ⏳ Lo que falta (requiere Azure)

- Crear la app en **Azure IoT Central** (`campus-ems`)
- Importar `iotcentral/device_template_campus_emergency_v1.json` como Device Template
- Registrar los 10 dispositivos (`campus-ems-01` al `campus-ems-10`)
- Correr `python/provision_devices.py` con el ID Scope y Master Key de la app → genera los connection strings
- Crear `.env` con esos connection strings y probar D1 primero
- Verificar D1 en Azure como **Connected** con telemetría llegando → luego D4 → luego el resto
- D8: probar `--send-to-cloud --disconnect-at N` y capturar el hueco en Azure
- D2: probar flujo completo Wokwi → MQTT → bridge → Azure

### ❌ No tocar todavía
Dashboard, reglas de alerta, históricos CSV de 4 días, screenshots finales — eso va después de tener los dispositivos conectados.

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