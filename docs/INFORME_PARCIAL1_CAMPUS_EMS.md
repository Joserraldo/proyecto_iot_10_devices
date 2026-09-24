# INFORME TÉCNICO DE PROYECTO — Parcial 1

## Escenario IoT Central con flota heterogénea de 10 dispositivos

**Campus UNAB — Gestión de Emergencias y Desastres**

> Universidad Autónoma de Bucaramanga · IoT + Cloud + Sistemas Distribuidos · Parcial 1 · 2026-II
>
> **Integrantes:** _[NOMBRES]_
> **Profesor:** _[NOMBRE]_
> **Fecha de entrega:** _[FECHA]_

---

<!-- ============================================================
INSTRUCCIONES PARA QUIEN GENERA EL DOCUMENTO FINAL (PRO):
Esta plantilla es la ESTRUCTURA del informe. Cada bloque con
"> **IMAGEN N:**" marca un punto exacto donde insertar una captura
real o un gráfico generado. La línea siguiente describe QUÉ debe
mostrar esa imagen para que puedas pedírsela al generador "pro".
Rellena los campos entre corchetes [ ] con la evidencia real del repo
(ver evidencias/ y docs/). No borres ninguna sección: todas son
exigidas por el enunciado del parcial.
============================================================ -->

## CONTENIDO (índice)

1. Portada y resumen ejecutivo
2. Historial de versiones
3. Arquitectura de referencia (con telecomunicaciones)
4. Catálogo de 10 dispositivos
5. Digital Twin y Device Template
6. Tablas de parámetros (datasheet + código)
7. Evidencia de asincronía y desconexión
8. Comparativa de variables — 4 días no consecutivos
9. Dashboard / Cuarto de Control
10. Sustentación presencial (2 códigos en vivo)
11. Repositorio y seguridad
12. Conclusiones y limitaciones
13. Anexos (capturas, logs, código)

---

# 1. Resumen ejecutivo

> **IMAGEN 1 — LOGO:** Logo de la "compañía" que opera el sistema (Campus EMS), con identidad visual propia. No usar el logo genérico de Azure.

Este proyecto despliega un **sistema de gestión de emergencias y desastres para el Campus UNAB** sobre **Azure IoT Central**, con una flota **heterogénea de 10 dispositivos** que monitorean: **meteorología, incendios, calidad del aire, perímetro/seguridad, evacuación y puesto de mando**.

La flota **no** se llena con un solo simulador: cada dispositivo envía desde un **origen distinto** (Digital Twin/SDK, Wokwi, Python, API pública, Atlas Weather, MQTT explícito, Replay CSV), lo que demuestra **asincronía**, **desconexiones controladas** y **operación en línea** durante una ventana de **4 días no consecutivos**.

**Resultados clave:**
- **10/10** dispositivos provisionados y asociados al template `campus-emergency-v1` (35 campos de telemetría).
- **7 orígenes de datos** distintos (requisito: ≥5).
- **6 intervalos de muestreo** (requisito: ≥3) → 15 s, 20 s, 30 s, 45 s, 60 s, 300 s.
- **1 desconexión controlada documentada** (D8, hueco de 120 s) y reconexión automática.
- **35 555 mensajes** de telemetría procesados en la ventana de evaluación.
- **Cuarto de control** propio (web) + Dashboard del portal de IoT Central.

---

# 2. Historial de versiones

> Obligatorio según la guía (sección 6). Debe reflejar la versión del **Device Template** y de **cada script** del repo.

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 0.1 | 2026-09-18 | _[Nombre]_ | Creación del Device Template `campus-emergency-v1` (v1.0.0) |
| 0.2 | 2026-09-19 | _[Nombre]_ | Primeros scripts Python (D1, D3, D4) |
| 0.3 | 2026-09-20 | _[Nombre]_ | Despliegue en VM, 10 nodos systemd operativos |
| 0.4 | 2026-09-23 | _[Nombre]_ | Fix asociación 10/10 al template; desconexión controlada D8 |
| 1.0 | 2026-09-24 | _[Nombre]_ | **Informe final** y evidencias completas |

> **IMAGEN 2 — VERSIÓN TEMPLATE:** Captura del portal de IoT Central mostrando la versión publicada del Device Template.

---

# 3. Arquitectura de referencia

## 3.1 Arquitectura en 4 capas

| Capa | Función | Componentes en el escenario |
|---|---|---|
| **1. Dispositivo** | Capturar datos del entorno | Estación meteo, incendio, calidad de aire, acceso, perímetro, evacuación, mando |
| **2. Telecomunicaciones** | Transporte seguro | MQTT/TLS (8883), HTTPS (443), MQTT (1883), DPS, Azure IoT Hub |
| **3. Plataforma** | Procesar y almacenar | Azure IoT Central, Device Template, Views, Rules, Data Explorer |
| **4. Operación** | Interacción humana | Cuarto de Control (web propio + portal), alarmas, exportación |

> **IMAGEN 3 — DIAGRAMA DE ARQUITECTURA (la imagen más importante del informe):**
> Diagrama de bloques que muestre:
> - **Origen de cada dispositivo (D1 a D10):** Wokwi, Python, API pública, MQTT explícito, CSV replay, Digital Twin.
> - **Capa de red:** Wi-Fi / 4G-LTE / puerto TLS 8883, con justificación de la salida a Internet del campus.
> - **Plataforma:** DPS → Azure IoT Hub → IoT Central.
> - **Capa de operación:** Views, Rules, Dashboard / Control Room.

## 3.2 Topología de red

```
  [ D1..D10 : Wokwi / Python / API / MQTT / CSV / Digital Twin ]
                        |
      MQTT/TLS (8883) / HTTPS (443) / MQTT (1883)
                        |
                 Azure IoT Hub (iotc-371f401d-...)
                        |
                      DPS (ID Scope 0ne012B4879)
                        |
                 Azure IoT Central (6284f58c-...azureiotcentral.com)
                        |
        Views · Rules · Data Explorer · Control Room Dashboard
```

## 3.3 Telecomunicaciones — justificación

| Protocolo | Puerto | Dispositivos | Justificación |
|---|---|---|---|
| MQTT/TLS | 8883 | D1, D3-D4, D9, D10 (SDK Python) | Telemetría periódica de baja latencia con cifrado |
| HTTPS | 443 | D5 (Open-Meteo), D6 (Atlas/WAQI) | Consumo de APIs públicas externas |
| MQTT | 1883 | D2 (Wokwi bridge), D7 (paho) | Simulación local / visibilidad explícita de protocolo |
| CSV replay | — | D8 | Datos históricos sin red |

**Mecanismos de resiliencia:** QoS 1, mensaje *will* (testamento MQTT), *reconnect backoff* exponencial, buffer local en CSV (D8).

---

# 4. Catálogo de 10 dispositivos

> Tabla central del informe (obligatoria en la guía, sección 6). Cada fila es un **origen de envío distinto**.

| ID | Zona / Rol | Origen de envío | Protocolo | Intervalo | Variables de telemetría | Datasheet / fuente |
|---|---|---|---|---|---|---|
| D1 | Área central | **Digital Twin (SDK)** | MQTT/TLS | 15 s | temperature, humidity, pressure, wind_speed, wind_direction, rainfall | Datasheet sensor meteorológico |
| D2 | Patio / cubierta | **Wokwi ESP32** (bridge) | MQTT | 30 s | temperature, humidity, lux | DHT22 + BH1750 |
| D3 | Incendio Bloque A | **Python SDK** | MQTT/TLS | 60 s | temperature, smoke, flame, co_level | Sensor humo MQ-2 |
| D4 | Incendio Laboratorio | **Python SDK** | MQTT/TLS | 60 s | temperature, smoke, flame, co_level, door_status | Sensor humo + contacto puerta |
| D5 | Calidad aire aula | **API pública (Open-Meteo)** | HTTPS | 15 s | temperature, humidity, wind_speed, wind_direction + co2_sim, pm25_sim, pm10_sim | Open-Meteo API |
| D6 | Calidad aire exterior | **Atlas Weather / WAQI** | HTTPS | 300 s | temperature, humidity, wind, aqi, pm25, pm10 | WAQI / Open-Meteo |
| D7 | Acceso principal | **MQTT explícito (paho)** | MQTT | 30 s | door_status, occupancy, temperature | Cliente Paho MQTT |
| D8 | Cerramiento norte | **Replay CSV 4 días** | MQTT/TLS | 60 s | motion, lux_nocturno, temperature, csv_row | Dataset histórico `perimetro_norte_4dias.csv` |
| D9 | Evacuación pasillo | **Digital Twin (SDK)** | MQTT/TLS | 45 s | occupancy, lux_emergency, temperature, emergency_status | Sensor ocupación + lux |
| D10 | Puesto de mando | **Digital Twin (SDK)** | MQTT/TLS | 20 s | connected_devices, disconnected_devices, system_health, temperatura_promedio, ack_* | Agregación de flota |

**Asincronía (6 intervalos distintos, requisito ≥3):** 15 s (D1, D5) · 20 s (D10) · 30 s (D2, D7) · 45 s (D9) · 60 s (D3, D4, D8) · 300 s (D6).

**Orígenes distintos (7, requisito ≥5):** Digital Twin/SDK, Wokwi, Python SDK, API pública, Atlas/WAQI, MQTT explícito, Replay CSV.

> **IMAGEN 4 — DEVICES EN CENTRAL:** Captura de la lista de 10 dispositivos en IoT Central con estado Connected/Disconnected, todos asociados al template.

---

# 5. Digital Twin y Device Template

## 5.1 Identidad del template

| Dato | Valor |
|---|---|
| Nombre | `campus-emergency-v1` |
| DTMI | `dtmi:campusems:campusEmergencyV1;1` |
| Campos de telemetría | **35** |
| Aplicación IoT Central | `6284f58c-3974-4537-9fba-a70fbb61a23a.azureiotcentral.com` |
| ID Scope DPS | `0ne012B4879` |
| IoT Hub | `iotc-371f401d-4819-4938-ad41-996a5a907560.azure-devices.net` |

## 5.2 Commands (acciones remotas)

| Comando | Descripción | Payload |
|---|---|---|
| `set_alert_thresholds` | Configurar umbrales de alerta desde la nube | temp_max, temp_min, humidity_max, co2_max |
| `reboot_device` | Reiniciar dispositivo remotamente | — |
| `test_sensors` | Probar sensores del dispositivo | sensor_list |
| `change_interval` | Cambiar intervalo de muestreo | interval (s) |

> **IMAGEN 5 — TEMPLATE / DIGITAL TWIN:** Captura del editor del Device Template mostrando la estructura de telemetría, propiedades writable y comandos.

---

# 6. Tablas de parámetros (datasheet + código)

> Obligatorio (guía sección 4 y 6): por variable → unidad, **rango del fabricante (datasheet)**, **rango operativo del escenario**, **precisión**, **umbral de Rule** y **valor usado en el código** (min/max/offset).

## 6.1 Parámetros por variable

| Variable | Unidad | Rango datasheet | Rango operativo | Precisión | Umbral Rule | Valor en código (min/max) |
|---|---|---|---|---|---|---|
| temperature | °C | -40 a +85 | -10 a +40 | ±0.5 °C | >35 °C (crítica) | D1: 20–30 · D3/D4: 19–33 |
| humidity | %HR | 0 a 100 | 20 a 80 | ±3 %HR | <5 o >98 % | D1: 47–70 |
| pressure | hPa | 300 a 1100 | 1000 a 1020 | ±1 hPa | — | D1: 1008–1018 |
| co_level | ppm | 0 a 500 | 0 a 50 | ±5 ppm | >600 ppm | D3/D4: 20–40 |
| smoke / flame | bool | — | — | — | true = alarma | — |
| co2_sim | ppm | 400 a 5000 | 400 a 2000 | ±50 ppm | >1500 ppm | D5: 400–1200 |
| pm25 / pm25_sim | µg/m³ | 0 a 500 | 0 a 150 | ±10 | >500 µg/m³ | D5: 5–25 · D6: 5–35 |
| pm10 | µg/m³ | 0 a 1000 | 0 a 300 | ±15 | — | D6: 10–70 |
| aqi | índice | 0 a 500 | 0 a 100 | ±5 | >350 | D6: 20–80 |
| wind_speed | m/s | 0 a 150 | 0 a 50 | ±0.5 m/s | — | D1: 2–8 |
| wind_direction | ° | 0 a 360 | 0 a 360 | ±5° | — | — |
| rainfall | mm | 0 a 200 | 0 a 50 | ±0.3 mm | — | D1: 0–5 |
| lux / lux_nocturno / lux_emergency | lx | 0 a 100 000 | 0 a 100 000 | ±1% | — | D9 lux_emergency: 0.1–200 |
| motion | bool | — | — | — | — | D8 |
| occupancy | cuenta | — | 0 a 10 | — | >80% | D7: 0–1 · D9: 0–2 |

## 6.2 Contrato de telemetría (35 campos)

Unidades: temperature/humedad °C y % · pressure hPa · viento m/s y ° · lluvia mm · lux lx · co/co2 ppm · pm µg/m³ · aqi índice · cuentas (occupancy, connected/disconnected_devices, ack_pending) · booleans (smoke, flame, door_status, motion) · strings (emergency_status, ack_status, mqtt_status, api_source, source, timestamp).

> **IMAGEN 6 — DATASHEET:** Tabla/gráfico de un datasheet real (p. ej. DHT22, MQ-2, BH1750) que ancle al menos un rango de la tabla anterior.

---

# 7. Evidencia de asincronía y desconexión

## 7.1 Asincronía — conteo de mensajes por dispositivo (ventana 2026-09-22 → 23)

| Device | Intervalo | Mensajes |
|---|---|---|
| D1 | 15 s | 8173 |
| D5 | 15 s | 7752 |
| D10 | 20 s | 6148 |
| D7 | 30 s | 4116 |
| D9 | 45 s | 2752 |
| D3 | 60 s | 2067 |
| D4 | 60 s | 2066 |
| D8 | 60 s (replay) | 2065 → 5760 |
| D6 | 300 s | 416 |
| D2 | 30 s (Wokwi) | cadencia vía bridge |

> **IMAGEN 7 — ASINCRONÍA:** Gráfico/gráficas de IoT Central (Data Explorer) superpuestas que evidencien los **distintos intervalos de muestreo** entre dispositivos (distancias entre puntos distintas por nodo).

## 7.2 Desconexión controlada — D8 Cerramiento norte

| Parámetro | Valor |
|---|---|
| Procedimiento | `D8_INTERVAL=60 sdk_node_d8.py --send-to-cloud --disconnect-at 3 --iterations 6` |
| T_desconexión | 2026-09-23 15:46:27.081 UTC |
| T_reconexión | 2026-09-23 15:48:27.081 UTC |
| Hueco de datos | **120 s** (2 intervalos de 60 s) |
| Estado antes | Connected |
| Estado durante | hueco en la serie / Disconnected |
| Estado después | reconexión automática (cliente MQTT/TLS del SDK) |

> **IMAGEN 8 — DESCONEXIÓN:** Captura del portal mostrando la serie `campus-ems-08` con el **hueco visible de 120 s**, y el estado Disconnected → Connected con la hora.
>
> **IMAGEN 9 — LOG RECONEXIÓN:** Log local (o dashboard) mostrando el reinicio del cliente y la reconexión.

---

# 8. Comparativa de variables — 4 días no consecutivos

> Obligatorio (guía sección 6): sobre los 4 días NO consecutivos, calcular **máximo, mínimo, promedio, recuento y sumatoria** (cuando aplique) y **relatar qué situación operativa explican esos extremos**.

## 8.1 Ventana de 4 días (D8 Cerramiento norte — dataset histórico)

Fechas: **2026-09-12 (sáb) · 2026-09-15 (mar) · 2026-09-19 (sáb) · 2026-09-22 (lun)** — 5760 filas @ 60 s.

| Día | rows | motion=1 | temp min | temp max | temp avg | lux min | lux max | lux avg |
|---|---|---|---|---|---|---|---|---|
| 2026-09-12 | 1440 | 373 | 14.0 | 28.1 | 20.50 | 0.0 | 51.1 | 20.80 |
| 2026-09-15 | 1440 | 341 | 14.0 | 28.5 | 20.51 | 0.0 | 51.3 | 20.82 |
| 2026-09-19 | 1440 | 329 | 14.0 | 28.2 | 20.52 | 0.0 | 50.8 | 20.71 |
| 2026-09-22 | 1440 | 312 | 14.0 | 28.2 | 20.49 | 0.0 | 50.4 | 20.68 |
| **Total** | **5760** | **1355** | 14.0 | 28.5 | 20.51 | 0.0 | 51.3 | 20.75 |

**Sumatorias:** temperatura 4 días = **118 150.1 °C**.

**Lectura operativa (relato):** el máximo de 28.5 °C ocurrió el **sáb 19 (tarde)**, el mínimo de 14.0 °C en las **madrugadas**; el lux alcanza hasta **51.3 lx** por el alumbrado perimetral nocturno; se registran **1355 detecciones de movimiento (23.5 %)**, más en **sábados (373) vs lunes (312)** → mayor tránsito perimetral el fin de semana.

## 8.2 Métricas EN VIVO de toda la flota (logs VM, 35 555 mensajes)

| Device | Variable | n | min | max | avg | suma |
|---|---|---|---|---|---|---|
| D1 | temperature | 8173 | 20.0 | 30.0 | 25.01 | 204 388.7 °C |
| D1 | humidity | 8173 | 47.1 | 69.9 | 58.44 | 477 600.2 % |
| D1 | pressure | 8173 | 1008.3 | 1018.2 | 1013.26 | 8 281 392.7 hPa |
| D1 | rainfall | 8173 | 0 | 5.0 | 0.72 | 5 852.4 mm |
| D3 | co_level | 2067 | 20.0 | 39.9 | 25.23 | 52 158.7 ppm |
| D4 | co_level | 2066 | 20.0 | 40.0 | 25.19 | 52 033.3 ppm |
| D5 | co2_sim | 7752 | 400 | 1200 | 809.10 | 6 272 137 ppm |
| D5 | pm25_sim | 7752 | 5 | 25 | 15.04 | 116 567.7 µg/m³ |
| D6 | aqi | 416 | 20 | 80 | 49.24 | 20 484 |
| D6 | pm25 | 416 | 5.0 | 34.9 | 19.93 | 8 292.2 µg/m³ |
| D6 | pm10 | 416 | 10.0 | 70.0 | 39.16 | 16 291.1 µg/m³ |
| D7 | occupancy | 4116 | 0 | 1 | 0.25 | 1 020 |
| D9 | occupancy | 2752 | 0 | 2 | 0.35 | 964 |
| D9 | lux_emergency | 2752 | 0.1 | 200.0 | 96.44 | 265 397.3 lx |
| D10 | connected_devices | 6148 | 8 | 10 | 9.02 | 55 434 |
| D10 | disconnected_devices | 6148 | 0 | 2 | 0.98 | 6 046 |
| D10 | system_health | 6148 | 85.0 | 100.0 | 92.47 | 568 480 % |

> **IMAGEN 10 — GRÁFICOS 4 DÍAS:** Gráfico(s) de IoT Central / Data Explorer de los 4 días no consecutivos (máx/mín/promedio) para al menos una variable clave (p. ej. temperatura campus, calidad de aire, ocupación).
>
> **IMAGEN 11 — COMPARATIVA:** Tabla o gráfico comparativo (barra/línea) de mínimo, máximo, promedio y recuento por día para el análisis.

---

# 9. Dashboard / Cuarto de Control

> Obligatorio (guía sección 7): el panel debe tener identidad visual propia y, visible al mismo tiempo: logo + nombre, estado de flota (Connected/Disconnected/Unassociated), **≥4 gráficos de telemetría** alineados a variables indispensables, **KPIs** (último valor, máx/mín del día), **bloque de alertas** y **mapa/esquema de zonas**.

## 9.1 Dashboard propio (web) — `parcialiot-jose-juancho.duckdns.org`

- Grid de 10 tarjetas con histórico a demanda.
- Navegación temporal: 1h / 6h / 24h / 72h / 7d, prev/next, salto de fecha.
- KPIs min/max por dispositivo, alertas por umbral.
- Botón **"Llamar asesor"** (email vía Brevo).
- Panel serial de Wokwi (D2).

## 9.2 Dashboard del portal — `Campus EMS - Control Room`

- Branding markdown + contador de flota (deviceCount).
- KPI temperatura, KPI humedad (avg 24 h), última lectura (LKV).
- Gráficos interactivos que enlazan al Data Explorer.

## 9.3 Los 4 gráficos mínimos recomendados

| Gráfico | Variable(s) | Dispositivos |
|---|---|---|
| 1. Temperatura promedio campus | temperature | D1, D3-D4, D5, D7, D9, D10 |
| 2. Calidad de aire aulas | co2_sim / pm25_sim | D5 |
| 3. Detección incendio (estado binario) | smoke / flame | D3, D4 |
| 4. Viento | wind_speed / wind_direction | D1 |

## 9.4 Mapa de zonas (esquema estático)

| Zona | Dispositivos |
|---|---|
| Área central / cubierta | D1, D2 |
| Bloques académicos (incendio) | D3, D4 |
| Aulas / exterior (calidad aire) | D5, D6 |
| Perímetro / acceso | D7, D8 |
| Evacuación | D9 |
| Puesto de mando | D10 |

> **IMAGEN 12 — CONTROL ROOM PORTAL:** Captura del dashboard del portal (logo, KPIs, gráficos, estado flota).
>
> **IMAGEN 13 — DASHBOARD PROPIO:** Captura del dashboard web propio (grid de tarjetas + KPIs + alertas).
>
> **IMAGEN 14 — MAPA ZONAS:** Esquema estático de zonas del campus con cada dispositivo ubicado en su lugar físico.

---

# 10. Sustentación presencial (2 códigos en vivo)

> Obligatorio (guía sección 8): en la sustentación se ejecutan **dos códigos en dos equipos distintos**, ambos deben aparecer en IoT Central y publicar al menos una variable **en vivo**.

## 10.1 Plan de sustentación

| Equipo | Código | Dispositivo | Qué se demuestra |
|---|---|---|---|
| **Portátil A** | `python/sdk_node_d1.py` (Python SDK/DPS) | D1 Estación meteo | Connected + telemetría viva (temp/humedad/viento) |
| **Portátil B** | Wokwi ESP32 (D2) + `python/mqtt_bridge_wokwi.py` | D2 Meteo patio | Connecting → Connected + respuesta a comando |

## 10.2 Guion de la demo (paso a paso)

1. Explicar escenario, Digital Twin y catálogo (por qué cada origen es distinto).
2. Mostrar el Control Room y navegar un gráfico de los 4 días no consecutivos.
3. Ejecutar **ambos códigos en equipos distintos**; verificar en IoT Central que publican **en vivo**.
4. **Reproducir una desconexión controlada** en uno de esos dos nodos y mostrar la **reconexión**.
5. Responder por umbrales, datasheets y limitaciones percibidas de IoT Central.

> **IMAGEN 15 — 2 EQUIPOS:** Captura (foto o pantalla) de los dos equipos corriendo en paralelo, con la vista de IoT Central mostrando ambos dispositivos en vivo.

---

# 11. Repositorio y seguridad

> Obligatorio (guía sección 6): README de decisiones, scripts **sin secretos en claro**, proyecto Wokwi, evidencias. Credenciales **solo por variable de entorno o DPS attested**.

| Elemento | Estado |
|---|---|
| Scripts de dispositivos (Python) | `python/` (D1–D10) |
| Firmware Wokwi | `wokwi/` (wokwi.ino, diagram.json) |
| Evidencias / datos | `evidencias/`, `data/`, `docs/` |
| Deployment VM (systemd) | `ops/` |
| Credenciales | Solo por `.env` / variables de entorno / DPS symmetric key. **Nunca** hardcodeadas en el repo |
| Config de despliegue | `ops/fleet.env.example` |

**Medidas de seguridad aplicadas:**
- Conexiones con **MQTT/TLS** (puerto 8883) para los nodos con SDK.
- **Provisionamiento DPS** con symmetric keys por dispositivo.
- Credenciales cargadas desde variables de entorno, no en el código fuente.
- `.env` y secretos excluidos del repo (`.gitignore`).

> **IMAGEN 16 — REPO / SEGURIDAD:** Captura de la estructura del repositorio y del `.env.example` (sin valores reales) demostrando que los secretos van por entorno.

---

# 12. Conclusiones y limitaciones

## 12.1 Conclusiones

- Se logró una flota **heterogénea de 10 dispositivos** con **7 orígenes de envío distintos**, todos asociados a un único Device Template de 35 campos.
- La **asincronía** (6 intervalos) y la **desconexión controlada** (D8) demuestran comportamiento real de campo, no una simulación uniforme.
- El **cuarto de control** (propio + portal) permite a un operador no programador validar el estado de la flota de un vistazo.
- La ventana de **4 días no consecutivos** permite análisis operativo (máx/mín/promedio/recuento/suma) con lectura de negocio.

## 12.2 Limitaciones percibidas de IoT Central

- _[Completar con las limitaciones reales encontradas, p. ej.:]_ límite de retención de datos del plan, dependencia de cuotas de APIs públicas (WAQI/Open-Meteo), exportación de datos no tan directa, etc.

---

# 13. Anexos

- **Anexo A:** Capturas del portal (guía `evidencias/guia_screenshots_
portal.md`, shots 1–8 + Rules + Control Room + Data Explorer).
- **Anexo B:** Capturas del dashboard propio (BITACORA §6, capturas 1–8).
- **Anexo C:** Logs de desconexión D8 (`evidencias/desconexion_d8_nueva_app.md`).
- **Anexo D:** Dataset D8 (`data/perimetro_norte_4dias.csv`) y análisis (`evidencias/analisis_perimetro_4dias.csv`).
- **Anexo E:** Matriz de orígenes (`docs/data-origin-matrix.md`), arquitectura (`docs/architecture.md`), control room (`docs/control-room.md`).
- **Anexo F:** Código fuente de los dos scripts usados en la sustentación.

---

*Fin del informe. Documento generado a partir del enunciado `Parcial_1_IoT_Central_v2.md` y de la evidencia del repositorio `proyecto_iot_10_devices`.*
