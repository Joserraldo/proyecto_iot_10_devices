# Arquitectura de 4 Capas - Azure IoT Central

## Escenario: Campus UNAB - Gestión de Emergencias (Opción 3.4)

## 📋 Visión General

La arquitectura está compuesta por 4 capas explícitas que garantizan la separación de responsabilidades, escalabilidad y mantenibilidad del sistema IoT.

---

## 🟦 Capa 1: Dispositivo (Device Layer)

**Propósito:** Capturar datos del entorno físico y enviarlos a la plataforma central.

### Componentes Principales:

| Sub-capacitación | Descripción | Ejemplos en el escenario |
|---|---|---|
| **Tipos de nodos** | Clasificaciones de dispositivos basadas en su función | Estación meteo, sensor incendio, sensor calidad aire, sensor acceso |
| **Orígenes de datos** | De dónde provienen las lecturas | Digital Twin, Wokwi simulación, Python SDK, API pública, Atlas Weather, CSV replay |
| **Sensores** | Hardware que captura las variables | Temperatura, humedad, CO₂, PM2.5, PM10, humo, llama, viento, lluvia, lux |
| **Actuadores** | Dispositivos que pueden ser controlados | Puertas, sistemas de ventilación, rociadores, alarmas |
| **Comunicación local** | Protocolos y medios de comunicación en el dispositivo | MQTT, HTTPS, CoAP, Wi-Fi, Ethernet, 4G/LTE |

### Protocolo por Tipo de Nodo:

| Dispositivo | Protocolo | Puerto | Características |
|---|---|---|---|
| Digital Twin (1-3) | MQTT/TLS | 8883 | Simulación en Azure, alta frecuencia |
| Wokwi (D2) | MQTT | 1883 | Local, comunicación bridge |
| Python SDK (D3-D4) | MQTT/TLS | 8883 | SDK azure-iot-device, DPS |
| API Pública (D5) | HTTPS | 443 | Consumo de endpoints externos |
| Atlas Weather (D6) | HTTPS | 443 | Feed meteorológico especializado |
| MQTT Explicito (D7) | MQTT | 1883 | Visibilidad de protocolo, Paho |
| Replay CSV (D8) | Local/Archivo | N/A | Datos históricos, sin red |
| Digital Twin (D9-D10) | MQTT/TLS | 8883 | Agregación y comandos |

### Restricciones del Dispositivo:

- Memoria limitada en nodos embedded (Wokwi, sensores simples)
- Variabilidad de conectividad (algún dispositivos pueden desconectarse)
- Consumo energético variable (baterías en algunos nodos)
- Precisión de sensor acotada por el datasheet del fabricante

---

## 🟨 Capa 2: Telecomunicaciones (Communications Layer)

**Propósito:** Transporte seguro y fiable de datos entre dispositivos y plataforma.

### Protocolos Soportados:

| Protocolo | Caso de Uso | Características Clave |
|---|---|---|
| **MQTT sobre TLS** | Telemetría periódica, baja latencia | QoS 0/1/2, retención de mensajes, 3 veces más eficiente que HTTP |
| **HTTPS** | APIs públicas, datos esporádicos | TLS 1.2+, JSON, ideal para consumos de API esporádicos |
| **MQTT sin cifrado** | Wokwi local, depuración | Sin seguridad, solo para pruebas locales |
| **CoAP** | Dispositivos muy limitados | UDP-based, menor overhead que HTTP |

### Topología de Red:

```
                    +----------------------+
                    |   Dispositivos (10)  |
                    |  Wokwi, Python,    |
                    |  Sensores, CSV      |
                    +----------+-----------+
                               |
                               | MQTT/TLS (8883) / HTTPS (443)
                               |
                               v
                    +----------------------+
                    |   Azure IoT Hub      |
                    |  (con IoT Central   |
                    |   sobre el hub)      |
                    +----------+-----------+
                               |
                               | DPS (Device Provisioning Service)
                               |
                               v
                    +----------------------+
                    |   Azure IoT Central  |
                    +----------------------+
```

### Configuración de DPS:

- **ID Scope:** `0ne000XXYYZZ` (compartido para todos los dispositivos)
- **Registration IDs:** `campus-ems-01` through `campus-ems-10`
- **Authentication:** Symmetric keys por dispositivo
- **Enrollment Type:** Individual enrollment (cada dispositivo tiene su propia key)

### Asincronía y Intervalos:

| Dispositivo | Intervalo | Justificación |
|---|---|---|
| D1 (Estación meteo) | 15 s | Condiciones cambiantes, detección rápida |
| D2 (Meteo patio) | 30 s | Monitoreo general, balance consumo/precisión |
| D3 (Incendio Bloque A) | 60 s | Eventos críticos requieren detección oportuna |
| D4 (Incendio Laboratorio) | 1 min | Sensores críticos, alta precisión |
| D5 (Calidad aire aula) | 15 s | Salud estudiantil, acción rápida si es necesario |
| D6 (Calidad aire exterior) | 5 min | Variables externas, cambio lento |
| D7 (Acceso principal) | 30 s | Seguridad, necesidad de respuesta oportuna |
| D8 (Cerramiento norte) | 1 min | Datos de perímetro, menor criticidad |
| D9 (Evacuación pasillo) | 45 s | Seguridad durante emergencias |
| D10 (Puesto mando) | 20 s | Agregación para toma de decisiones |

### Mecanismos de Resiliencia:

- **QoS 1** como mínimo para telemetría crítica (incendios, acceso)
- **Will message** (testamento MQTT) para detección de desconexiones
- **Reconnect backoff** exponencial en el cliente Python
- **Buffer local** en dispositivos con almacenamiento (CSV replay para D8)

---

## 🟩 Capa 3: Plataforma (Platform Layer)

**Propósito:** Procesar, almacenar y visualizar los datos provenientes de la capa de comunicaciones.

### Componentes Principales:

| Componente | Función | Tecnología |
|---|---|---|
| **IoT Central** | Plataforma SaaS completa, dashboards, reglas | Azure PaaS |
| **IoT Hub** | Capa de bajo nivel, protocolo, identidad | Azure PaaS (subyacente) |
| **DPS** | Provisionamiento automático de dispositivos | Azure PaaS |
| **Azure Storage** | Almacenamiento de blobs, datos históricos | Azure Blob Storage |
| **Time Series Insights** | Análisis de series temporales | Azure Analytics |
| **Power BI** | Visualización avanzada y reportes | Power BI Desktop + Service |
| **Function Apps** | Lógica serverless, transformación de datos | Azure Functions |

### Device Templates en IoT Central:

- **Template name:** `campus-emergency-v1`
- **Variables definidas:** 25+ campos de telemetría
- **Propiedades writable:** 6 configurables
- **Commands:** 4 acciones remotas
- **Views personalizadas:** 8 vistas por zona/funcionalidad
- **Dashboard Control Room:** 1 dashboard principal

### Reglas de Negocio (Rules Engine):

| Rule | Condición | Acción |
|---|---|---|
| `temp_critica` | temperature > 40°C por 5 min | Notificación push, email, SMS |
| `humedad_extrema` | humidity < 20% o > 80% | Alertar mantenimiento HVAC |
| `calidad_aire_peligrosa` | pm25 > 55 μg/m³ | Activar purificadores, notificar |
| `incendio_detectado` | smoke = true O flame = true | Alarma sonora, notificar bomberos, evacuación |
| `acceso_nocturno` | door_status = true y hora 00:00-06:00 | Seguridad privada, reporte |
| `evacuacion_activa` | multiple smoke sensors activadas | Sistemas de rociadores, guía evacuación |

### Time Settings:

- **Timezone:** America/Argentina/Buenos_Aires (o zona horaria del campus)
- **Data retention:** 30 días en IoT Central, 1 año en Blob Storage
- **SLA:** 99.9% de disponibilidad de la plataforma

---

## 🟦 Capa 4: Operación (Operations Layer)

**Propósito:** Interacción humana, toma de decisiones y gestión operativa del sistema.

### Componentes Principales:

| Componente | Descripción | Propósito |
|---|---|---|
| **Control Room (Dashboard)** | Interfaz unificada con KPIs, gráficos, mapa | Monitoreo en tiempo real, decisiones operativas |
| **Views** | Agrupaciones lógicas de dispositivos por zona | Organización administrativa, filtros por área |
| **Alertas** | Notificaciones por umbrales críticos | Respuesta rápida a incidentes |
| **Gestión de Usuarios** | Roles y permisos (admin, operador, viewer) | Seguridad, acceso controlado |
| **Reportes** | Generación de informes históricos | Cumplimiento, análisis estacional, sustentación |

### Dashboard - Cuarto de Control (Control Room):

#### Elementos Mínimos (por requisito del parcial):

1. **Identidad Visual:**
   - Logo UNAB institucional
   - Título: "Dashboard Gestión de Emergencias - Campus UNAB"
   - Colores institucionales

2. **Métricas de Flota:**
   - Contador total de dispositivos: **10**
   - `Connected`: Número de dispositivos conectados en tiempo real
   - `Disconnected`: Número de dispositivos con conexión perdida
   - `Unassociated`: Número de dispositivos no asociados

3. **Visualización de Telemetría:**
   - **Mínimo 4 gráficos interactivos** alineados con variables del escenario:
     - Gráfico 1: Temperatura promedio campus (última hora)
     - Gráfico 2: Calidad de aire aulas (CO₂ en tiempo real)
     - Gráfico 3: Detección de humo/incendios (estado binario)
     - Gráfico 4: Velocidad y dirección del viento

4. **Tarjetas KPI:**
   - Última lectura de temperatura (°C)
   - Máximo de hoy (°C)
   - Mínimo de hoy (°C)
   - Promedio de humedad (%)
   - Calidad de aire actual (CO₂ ppm)

5. **Gestión de Alarmas:**
   - Lista de alarmas activadas
   - Prioridad (crítica, advertencia, info)
   - Botón ACK (acknowledgement) para cada alerta
   - Historial de alarmas disparadas durante la ventana de 4 días

6. **Mapa de Distribución:**
   - Ubicación física de los 10 nodos por zonas del campus
   - Íconos diferenciados por tipo de dispositivo
   - Estado en tiempo real (Conectado/Desconectado)
   - Tooltip con variables principales al pasar el mouse

### Operaciones Soportadas:

- **Monitoreo en tiempo real:** Todos los dispositivos visibles con estado Connect/Disconnect
- **Búsqueda por zona:** Filtrar por bloque, área, tipo de sensor
- **Exportación de datos:** CSV, JSON para análisis externos
- **Comandos remotos:** Reiniciar dispositivo, cambiar intervalo, ajustar umbrales
- **Historial temporal:** Seleccionar rangos de fecha (últimas 24h, 7 días, 30 días)

### Troubleshooting Operativo:

| Síntoma | Causa Probable | Acción |
|---|---|---|
| No hay datos en dashboard | Dispositivo desconectado | Verificar conectividad, reiniciar dispositivo |
| Valores extremos en telemetría | Fuera de rango sensor | Verificar calibración, revisar datasheet |
| Alarmas falsas | Umbrales muy sensibles | Ajustar alert_thresholds en Device Template |
| Retraso en telemetría | Congestión de red | Revisar intervalos, optimizar MQTT QoS |
| No se pueden registrar comandos | Fallo DPS | Verificar registration ID y scope |

### Documentación de Operación:

- **Manual de usuario:** Instrucciones para operadores del cuarto de control
- **Guía de troubleshooting:** Problemas comunes y soluciones
- **Bitácora de mantenimiento:** Registro de acciones correctivas y preventivas
- **Procedimiento de respaldo:** Cómo exportar y guardar datos críticos

---

## 📊 Resumen de la Arquitectura

| Capa | Enfoque | Tecnologías Clave | Responsable |
|---|---|---|---|
| **1. Dispositivo** | Captura y envío de datos | Sensores, MQTT, Python, Wokwi | Integrantes hardware |
| **2. Telecomunicaciones** | Transporte seguro | MQTT/TLS, HTTPS, DPS, Azure IoT Hub | Integrantes infraestructura |
| **3. Plataforma** | Procesamiento y almacenamiento | IoT Central, Azure Functions, Blob Storage | Integrantes datos |
| **4. Operación** | Interacción y gestión | Dashboards, Views, Alertas, Reportes | Integrantes UX/ops |

**Objetivo Final:** Sistema completo y operacional donde los 10 dispositivos heterogéneos envían datos asíncronos a Azure IoT Central, con visualización en un dashboard tipo Control Room, soporte para análisis de 4 días no consecutivos, y capacidad para detectar y recuperarse de desconexiones controladas.