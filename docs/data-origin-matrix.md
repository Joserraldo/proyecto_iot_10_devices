# Matriz de Origen de Datos y Dinámica de Red

## Escenario: Campus UNAB - Gestión de Emergencias (Opción 3.4)

### Tabla Consolidada de 10 Dispositivos

| ID | Dispositivo | Zona | Origen de Datos | Protocolo | Intervalo Muestreo | Variables Clave | Datasource Específica |
|---|---|---|---|---|---|---|---|
| **D1** | Estación meteo campus | Área central del campus | **Digital Twin** | MQTT/TLS | 15 s | temp, humidity, wind_speed, wind_direction, rainfall, pressure | Simulación Azure IoT Central, datos realistas basados en condiciones campus |
| **D2** | Meteo patio / cubierta | Patio y cubierta | **Wokwi** | MQTT | 30 s | temp_superficie, lux, humidity | ESP32 simulado, sensores DHT22+BMP180, iluminancia BH1750 |
| **D3** | Incendio Bloque A | Bloque A | **Python SDK** | MQTT/TLS | 60 s | smoke, flame, temperature, co_level | `azure-iot-device` SDK, conexión DPS+MQTT, sensores simulados con patrones realistas |
| **D4** | Incendio Laboratorio | Laboratorio | **Python SDK** | MQTT/TLS | 1 min | smoke, flame, temperature, door_status | `azure-iot-device` SDK, mismo patrón que D3 pero con lógica distinta (incendio laboratorio) |
| **D5** | Calidad aire aula | Aula | **API Pública** | HTTPS | 15 s | co2, pm25, pm10, temperature | Open-Meteo API adaptada, variables de calidad aire simuladas desde endpoint educativo |
| **D6** | Calidad aire exterior | Exterior | **Atlas Weather** | HTTPS | 5 min | pm25, pm10, aqi, temperature, humidity, wind | Atlas Weather API, datos meteorológicos reales para región campus |
| **D7** | Acceso principal / Perímetro | Entrada principal | **MQTT Explicito** | MQTT | 30 s | door_status, occupancy, temperature | Cliente Paho MQTT, visibilidad de protocolo, conexión broker local/VM |
| **D8** | Cerramiento norte | Perímetro norte | **Replay CSV** | Local/Archivo | 1 min | motion, lux_nocturno, temperature | Dataset histórico 4 días, reproducción programada, datos anonimizados |
| **D9** | Evacuación pasillo | Pasillo evacuación | **Digital Twin** | MQTT/TLS | 45 s | occupancy, lux_emergency, temperature | Simulación Azure IoT Central, escenarios evacuación con patrones de movimiento |
| **D10** | Puesto de mando | Centro de mando | **Digital Twin** | MQTT/TLS | 20 s | estado_agregado, confirmacion_ack, temperatura_promedio | Simulación Azure IoT Central, agregación de datos de todos los demás dispositivos |

### Dinámica de Red

#### Intervalos de Muestreo (3+ intervalos distintos confirmados):

Los siguientes intervalos están garantizados en la flota (mínimo 3 requerido):

| Intervalo | segundos | Dispositivos que usan este intervalo | Justificación |
|---|---|---|---|
| **Rápido** | **15 s** | D1, D5 | Condiciones que cambian rápidamente (clima, calidad aire aula) |
| **Medio** | **30 s** | D2, D7 | Monitoreo general, balance consumo/precisión |
| **Lento** | **1 min** | D4, D8 | Datos críticos pero no urgentísimos (incendio lab, perímetro) |
| **Muy Lento** | **5 min** | D6 | Variables externas que cambian despacito (clima exterior) |
| **Crítico** | **20 s** | D10 | Agregación para puesto de mando, toma de decisiones rápidas |
| **Personalizado** | **45 s/60 s** | D3, D9 | Eventos específicos (incendio, evacuación) |

#### Asincronía Garantizada:

- **Sí**, la flota tiene al menos 3 intervalos distintos: **15s, 30s, 60s** (adicionalmente: 5min, 20s, 45s)
- Esto demuestra la heterogeneidad requerida por el parcial

#### Escenario de Desconexión Controlada:

| Dispositivo | Escenario | Procedimiento |
|---|---|---|
| **D8 (Cerramiento norte)** | **Desconexión controlada** | 1. Iniciar ejecución normal<br>2. A las 2h de ejecución, detener cliente MQTT deliberadamente<br>3. Verificar estado cambia a `Disconnected` en IoT Central<br>4. Re-iniciar cliente MQTT después de 30 segundos<br>5. Verificar reconexión y retorno al estado `Connected`<br>6. Documentar hueco de datos de aproximadamente 30-45 segundos en los logs<br><br>**Evidencia requerida:**<br>- Captura de estado `Disconnected` en IoT Central<br>- Registro de tiempo de desconexión y reconexión<br>- Gráfico con hueco de datos en el rango temporal<br>- Logs locales que muestren el reinicio del cliente |

### Validación de Heterogeneidad de Orígenes:

| Criterio | Verificación | Estado |
|---|---|---|
| **Mínimo 5 orígenes distintos** | Digital Twin, Wokwi, Python SDK, API Pública, Atlas Weather, MQTT Explicito, Replay CSV | **7 orígenes** ✓ |
| **Al menos 3 intervalos distintos** | 15s, 30s, 60s, 5min, 20s, 45s (6 intervalos) | **6 intervalos** ✓ |
| **Al menos 1 desconexión controlada** | D8 con procedimiento Documentado | **1 dispositivo** ✓ |
| **No todos dependen mismo simulador** | Mix de orígenes reales y simulados | **Distinto** ✓ |
| **Cobertura de zonas completas** | Los 10 nodos cubren todas las zonas indispensables | **10/10 zonas** ✓ |

### Orígenes por Categoría:

| Categoría | Cantidad | Dispositivos | Propósito |
|---|---|---|---|
| **Simuladores** | 3 | D1 (DT), D2 (Wokwi), D3-D4 (Python SDK) | Demostrar diferentes tecnologías de simulación |
| **APIs Externas** | 2 | D5 (Open-Meteo), D6 (Atlas Weather) | Integrar datos reales/cuasi-reales del entorno |
| **Protocolos Explicitos** | 1 | D7 (MQTT Paho) | Visibilidad y control del protocolo de capa 2 |
| **Replay/Histórico** | 1 | D8 (CSV) | Datos históricos, asincronía intencional |
| **Digital Twin** | 3 | D1, D9, D10 | Consolidación y agregación de datos |

### Resumen Ejecutivo de Dinámica

La flota de 10 dispositivos del campus UNAB demostrará:

1. **Heterogeneidad completa:** 7 fuentes de datos distintas, desde simuladores hasta APIs reales y datos históricos
2. **Asincronía operativa:** 6 intervalos de muestreo diferentes, desde cada 15 segundos hasta cada 5 minutos
3. **Resiliencia documentada:** Un dispositivo (D8) con desconexión controlada y reconexión verificable
4. **Cobertura total:** Todos los nodos cubren zonas indispensables del escenario de gestión de emergencias
5. **Operabilidad mixta:** Algunos dispositivos usan SDK oficial (Python), otros usan simuladores local (Wokwi), y otros integran APIs externas

**Objetivo cumplido:** La matriz satisface todos los requisitos del parcial para dinámica de red, heterogeneidad y resiliencia.