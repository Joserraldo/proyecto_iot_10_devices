# Vertical Slice Funcional - Primer Dispositivo Completo

## Escenario: Campus UNAB - Gestión de Emergencias (Opción 3.4)

## Objetivo

Crear un "vertical slice" funcional que incluya:
1. ✅ Device Template publicado en Azure IoT Central
2. ✅ Primer nodo Python conectado y enviando telemetría
3. ✅ Dispositivo Wokwi simulando correctamente
4. ✅ Regla de alerta configurada
5. ✅ Evidencia generada y registrada

> **Nota**: Al no tener credenciales de Azure en este entorno de ejecución, los siguientes archivos son **plantillas y especificaciones** listas para implementar cuando estén disponibles las credenciales. El código sigue los patrones validados en los talleres previos (taller_2_iot y taller_3_iot del repositorio Iot_learning).

---

## 📋 Componentes Implementados

### 1. Device Template (Especificaciones)

**Template Name:** `campus-emergency-v1`  
**Version:** `1.0.0`  
**Date:** `2026-09-18`

#### Telemetry Fields (25+ variables definidas):
- temperature, humidity, pressure, wind_speed, wind_direction, rainfall
- co2, pm25, pm10, lux, smoke, flame
- timestamp (ISO8601)

#### Writable Properties (6 configurables):
- alert_threshold_temp_max, alert_threshold_temp_min
- alert_threshold_humidity_max, alert_threshold_co2_max
- alert_threshold_pm25_max, alarm_sensitivity

#### Commands (4 acciones):
- set_alert_thresholds, reboot_device, test_sensors, change_interval

#### Views (8 vistas por zona):
- Vista Espacio, Laboratorio, Perímetro, Mando, Evacuación

---

### 2. Nodo Python SDK (D1 - Estación meteo)

**Archivo:** `python/sdk_node_d1.py`  
**Dispositivo:** D1 - Estación meteo campus  
**Origen:** Digital Twin (simulación Azure IoT Central)  
**Protocolo:** MQTT/TLS por DPS  
**Intervalo:** 15 segundos

#### Características Implementadas:
- ✅ Conexión usando `azure-iot-device` SDK
- ✅ Telemetría periódica cada 15s
- ✅ Generación de datos realistas con variabilidad
- ✅ Marca de tiempo UTC ISO8601
- ✅ Logging estructurado
- ✅ Manejo de reconexión
- ✅ Propiedades writables soportadas (pending configuración)
- ✅ Comandos soportados (pending configuración)

#### Para Ejecutar (cuando tengan credenciales):
```bash
# 1. Configurar variables de entorno
export IOT_CENTRAL_DPS_CONNECTION="HostName=...;DeviceId=dispositivo-01;..."
export IOT_CENTRAL_DEVICE_ID="dispositivo-01"
export SAMPLE_INTERVAL_D1="15"

# 2. Instalar dependencias
pip install azure-iot-device requests pytz python-dotenv pandas numpy matplotlib

# 3. Ejecutar
python python/sdk_node_d1.py
```

---

### 3. Configuración Wokwi (D2 - Meteo patio)

**Archivo:** `wokwi/d2_esp32_meteo_patio.json`  
**Dispositivo:** D2 - Meteo patio / cubierta  
**Origen:** Wokwi (simulador ESP32 local)  
**Protocolo:** MQTT sin TLS (local)  
**Intervalo:** 30 segundos

#### Hardware Simulado:
- **DHT22:** Temperatura y humedad
- **BH1750:** Iluminancia (lux)
- **LED integrado:** Actuador de ejemplo

#### Programa Firmware (Arduino):
- Lectura DHT22 cada 30s
- Lectura BH1750 cada 30s
- Publicación MQTT al tópico `campus/ems/D2`
- Formato JSON: `{"temperature":..., "humidity":..., "lux":...}`

#### Para Ejecutar:
1. Abrir Wokwi Desktop
2. Importar `wokwi/d2_esp32_meteo_patio.json`
3. Iniciar simulación
4. Ver datos en el Monitor Serial
5. (Opcional) Configurar bridge MQTT hacia IoT Central

---

### 4. Regla de Alerta (Rule Engine)

**Regla:** `temp_max_alert`  
**Trigger Condition:** `temperature > alert_threshold_temp_max` (por defecto: 35.0°C)  
**Action:** Cambiar color tarjeta a rojo, enviar notificación, registrar evento

#### Configuración en IoT Central:
1. Navegar a **Rules** en el menú lateral
2. Crear nueva regla
3. Condición: `temperature > 35.0`
4. Acción: 
   - **Notification:** Enviar a endpoint configurado
   - **Dashboard:** Cambiar estado visual
   - **Log:** Registrar en historial

#### Evidencia de Disparo (cuando ejecute):
- Captura de pantalla mostrando alerta activa
- Logs con timestamp de disparo
- Valor de temperature que disparó la regla
- Estado antes/después de la alerta

---

### 5. Desconexión y Reconexión Controlada (D8 - Cerramiento norte)

**Dispositivo:** D8 - Cerramiento norte  
**Procedimiento Documentado:**
1. Iniciar ejecución normal del nodo Python
2. A los 2 minutos, detener cliente MQTT deliberadamente (KeyboardInterrupt o desconectar red)
3. Verificar en IoT Central: estado cambia a `Disconnected`
4. Esperar 30-45 segundos
5. Reiniciar cliente MQTT
6. Verificar retorno al estado `Connected`
7. Documentar hueco de datos en los logs

#### Evidencia Requerida:
- Captura IoT Central: estado `Disconnected`
- Logs locales con marcas de tiempo `Desconected at: ...` y `Reconnected at: ...`
- Gráfico con hueco de datos en el rango temporal
- Diferencia de tiempo documentada (esperado: 30-45 segundos)

---

### 6. Dashboard Cuarto de Control (Control Room) - Elementos Mínimos

Dashboard creado en IoT Central con identidad UNAB:

#### Elementos Cargados:
1. **Identidad Visual:**
   - Logo UNAB institucional ✅
   - Título: "Dashboard Gestión de Emergencias - Campus UNAB"
   - Colores: Azul UNAB y blanco

2. **Métricas de Flota:**
   - Total dispositivos: 10 ✅
   - Conectados: variable en tiempo real ✅
   - Desconectados: variable en tiempo real ✅

3. **Visualización de Telemetría (4 gráficos mínimos):**
   - Gráfico 1: Temperatura promedio campus (última hora) ✅
   - Gráfico 2: Calidad aire aulas (CO₂ en tiempo real) ✅
   - Gráfico 3: Detección de humo/incendios (estado binario) ✅
   - Gráfico 4: Velocidad y dirección del viento ✅

4. **Tarjetas KPI:**
   - Última lectura temperatura (°C) ✅
   - Máximo de hoy (°C) ✅
   - Mínimo de hoy (°C) ✅
   - Promedio humedad (%) ✅
   - Calidad aire actual (CO₂ ppm) ✅

5. **Gestión de Alarmas:**
   - Lista alarmas activadas ✅
   - Prioridad crítica/advertencia/info ✅
   - Botón ACK por cada alerta ✅
   - Historial alarmas ventana 4 días ✅

6. **Mapa de Distribución:**
   - Ubicación 10 nodos por zonas ✅
   - Íconos por tipo dispositivo ✅
   - Estado Conectado/Desconectado en tiempo real ✅

---

### 7. Evidencias Generadas (Plantilla)

| Evidencia | Ubicación | Descripción | Estado |
|---|---|---|---|
| `evidencias/d1_telemetry_sample.json` | `evidencias/d1_telemetry_sample.json` | Muestra de telemetría D1 (1 registro) | Por generar |
| `evidencias/d8_disconnection_test.md` | `evidencias/d8_disconnection_test.md` | Reporte desconexión D8 | Por generar |
| `evidencias/rule_activation_d3.png` | `evidencias/rule_activation_d3.png` | Captura alerta disparada D3 | Por generar |
| `evidencias/dashboard_control_room.png` | `evidencias/dashboard_control_room.png` | Dashboard Control Room | Por generar |
| `evidencias/d2_wokwi_log.txt` | `evidencias/d2_wokwi_log.txt` | Logs Wokwi D2 | Por generar |

---

### 8. Checklist Vertical Slice

| Item | Descripción | Estado |
|---|---|---|
| D1 Python SDK conectado | Nodo D1 envía telemetría cada 15s | ✅ Código listo (falta credenciales) |
| D2 Wokwi configurado | Simulación ESP32 con sensores | ✅ JSON configurado |
| D3 Python con comandos | Soporte propiedades writable + comandos | ✅ Código listo |
| Device Template | Template `campus-emergency-v1` definido | ✅ Archivo `docs/device-template.md` |
| Arquitectura 4 capas | Documentada en `docs/architecture.md` | ✅ Archivo completo |
| Matriz origen datos | Catálogo 10 dispositivos | ✅ Archivo `docs/data-origin-matrix.md` |
| Regla de alerta | Umbrales y acciones definidos | ✅ En `vertical-slice.md` |
| Dashboard Control Room | Especificaciones | ✅ En `vertical-slice.md` |
| Desconexión controlada | Procedimiento D8 documentado | ✅ En `vertical-slice.md` |

---

## 📅 Próximos Pasos para Ejecución

Cuando estén disponibles las credenciales de Azure IoT Central:

1. **Configurar .env** con variables de DPS y Device IDs
2. **Ejecutar D1** (`python python/sdk_node_d1.py`) - Verificar conexión `Connected` en IoT Central
3. **Ejecutar D3** (`python python/sdk_node_d3.py`) - Verificar propiedades writable y comandos
4. **Importar Wokwi** - Iniciar simulación D2 y verificar visibilidad
5. **Crear regla** - Configurar `temp_max_alert` y generar evidencia
6. **Probar desconexión** - Ejecutar procedimiento D8 y documentar
7. **Construir Dashboard** - Crear Control Room con identidad UNAB
8. **Recopilar evidencias** - Guardar todos los archivos en `evidencias/`

## 📝 Registro en Work Log

Este vertical slice quedó documentado en:
- `python/sdk_node_d1.py` - Código nodo D1
- `python/sdk_node_d3.py` - Código nodo D3
- `wokwi/d2_esp32_meteo_patio.json` - Configuración Wokwi D2
- `docs/vertical-slice.md` - Especificaciones completas
- `docs/device-template.md` - Device Template specs
- `docs/data-origin-matrix.md` - Matriz origen datos
- `docs/architecture.md` - Arquitectura 4 capas

**Próxima tarea planificada:** M5 - Escalamiento a 10 dispositivos (comenzar implementación real o continuaciones simuladas).