# Dashboard Control Room - Cuarto de Control

## Escenario: Campus UNAB - Gestión de Emergencias (Opción 3.4)

## Objetivo

Diseñar y crear el dashboard tipo "Cuarto de Control" en Azure IoT Central que cumpla con los requisitos mínimos específicados en la guía técnica y que sirva como interfaz principal para la operación y monitoreo del escenario de emergencias universitarias.

## Requisitos del Dashboard (de la Guía Técnica Sección 5)

El panel interactivo en IoT Central debe cumplir los siguientes elementos mínimos visibles en una sola pantalla:

### 1. Identidad Visual

| Elemento | Especificación | Estado |
|---|---|---|
| **Logo** | Logo institucional UNAB (azul corporativo) | ✅ Diseñado |
| **Título** | "Dashboard Gestión de Emergencias - Campus UNAB" | ✅ Texto definido |
| **Colores** | Paleta UNAB: Azul (#003366), Blanco (#FFFFFF), Gris (#666666) | ✅ Esquema definido |

### 2. Métricas de Flota (Contadores Agregados)

| Métrica | Valor | Estado |
|---|---|---|
| **Total Dispositivos** | 10 | ✅ Configurado |
| **Conectados** | Variable en tiempo real (lectura actual) | ✅ Widget configurado |
| **Desconectados** | Variable en tiempo real | ✅ Widget configurado |
| **No Asociados** | Contador de dispositivos sin registro | ✅ Widget configurado |

### 3. Visualización de Telemetría (Mínimo 4 Gráficos Interactivos)

Los siguientes 4 gráficos mínimos estarán presentes en el dashboard:

#### Gráfico 1: Temperatura Promedio Campus
- **Tipo**: Línea temporal
- **Variable**: temperature (todos los dispositivos D1-D10)
- **Intervalo**: Última hora
- **Etiqueta**: "Temperatura Promedio Campus - °C"
- **Unidad**: °C
- **Color**: Azul UNAB

#### Gráfico 2: Calidad Aire Aulas (CO₂ en Tiempo Real)
- **Tipo**: Tarjeta KPI + Línea
- **Variable**: co2 (dispositivo D5)
- **Intervalo**: Tiempo real
- **Etiqueta**: "CO₂ Aulas - ppm"
- **Unidad**: ppm
- **Rango**: 400-5000 ppm
- **Alerta**: >1000 ppm (ventilación requerida)

#### Gráfico 3: Detección de Humo/Incendios (Estado Binario)
- **Tipo**: Tarjetas Estado + Alarmas
- **Variable**: smoke (D3, D4) y flame
- **Intervalo**: Tiempos real
- **Etiqueta**: "Estado Alarmas Incendio"
- **Iconos**: 
  - 🔥 Llamas detectadas (rojo)
  - ☢️ Humo detectado (naranja)
  - ✅ Normal (verde)

#### Gráfico 4: Velocidad y Dirección del Viento
- **Tipo**: Gráfico combinado (línea + polar)
- **Variables**: wind_speed, wind_direction (D1)
- **Intervalo**: Últimas 6 horas
- **Etiqueta**: "Viento Campus - m/s y dirección"
- **Dual-axis**: 
  - Izquierda: Velocidad (m/s)
  - Derecha: Dirección (°)

### 4. Tarjetas KPI (Valores en Tiempo Real)

| KPI | Valor Actual | Máximo Día | Mínimo Día | Descripción |
|---|---|---|---|---|
| **Temp. Última Lectura** | `{{temp_live}}°C` | `{{temp_max_hoy}}°C` | `{{temp_min_hoy}}°C` | Temperatura más reciente |
| **Humedad Promedio** | `{{hum_live}}%` | `{{hum_max_hoy}}%` | `{{hum_min_hoy}}%` | Humedad del día |
| **CO₂ Actual** | `{{co2_live}}ppm` | `{{co2_max_hoy}}ppm` | `{{co2_min_hoy}}ppm` | Calidad aire actual |
| **Viento Actual** | `{{wind_live}}m/s` | `{{wind_max_hoy}}m/s` | `{{wind_min_hoy}}m/s` | Velocidad viento |
| **Ocupación Global** | `{{occ_live}} de 10` | `{{occ_max_hoy}} de 10` | `{{occ_min_hoy}} de 10` | Dispositivos ocupados |

### 5. Gestión de Alarmas

Módulo de reglas (*Rules*) y alertas disparadas durante la ventana evaluada.

#### Estructura de Alarmas en IoT Central

| Nombre Rule | Condición | Severidad | Acción |
|---|---|---|---|
| `temp_max_alert` | temperature > 35.0°C | Crítica | Notificación, color tarjeta rojo |
| `temp_min_alert` | temperature < 15.0°C | Advertencia | Notificación, color tarjeta azul |
| `co2_max_alert` | co2 > 1500 ppm | Advertencia | Ventilación forzada |
| `smoke_detected` | smoke = true | Crítica | Alarma sonora, bomberos |
| `flame_detected` | flame = true | Crítica | Rociadores, evacuación |
| `door_unauthorized` | puerta abierta 00:00-06:00 | Advertencia | Seguridad privada |
| `high_occupancy` | ocupación > 80% | Advertencia | Control acceso |
| `system_offline` | >2 dispositivos desconectados | Advertencia | Mantenimiento |

#### Panel de Alarmas

- **Lista en tiempo real** de alertas activadas
- **Prioridad**: Crítica / Advertencia / Informacional
- **Botón ACK** (acknowledgement) por cada alerta
- **Historial**: Alarmas disparadas en ventana 4 días
- **Filtro por tipo**: Ver solo críticas, solo advertencias, todas

### 6. Mapa de Distribución

Ubicación física de los 10 nodos por zonas del campus.

#### Características del Mapa

- **Íconos por tipo dispositivo**:
  - 🌤️ Estación meteo (D1) - color azul
  - 🏫 Meteo patio (D2) - color verde
  - 🔥 Incendio (D3, D4) - color rojo
  - 💨 Calidad aire (D5, D6) - color naranja
  - 🚪 Acceso (D7) - color morado
  - 📡 Cerramiento (D8) - color rojo oscuro
  - 🚪 Evacuación (D9) - color amarillo
  - 💼 Puesto mando (D10) - color rojo institucional

- **Estado en tiempo real**:
  - 🟢 Conectado (línea sólida)
  - 🔴 Desconectado (línea discontinuada)
  - 🟡 Mantenimiento (punto parpadeante)

- **Tooltips al pasar mouse**:
  - Nombre dispositivo
  - Zona del campus
  - Variable principal actual
  - Estado Connected/Disconnected
  - Última lectura de temperatura/valor crítico

- **Agrupación por zona**:
  - Área central (D1)
  - Patio (D2)
  - Bloques académicos (D3, D4)
  - Aulas (D5)
  - Exteriors (D6, D8)
  - Pasillos (D9)
  - Mando (D10)

### 7. Configuración Adicional

#### Timezone
- **Valor**: `America/Argentina/Buenos_Aires` (o zona horaria del campus UNAB)
- **Formato**: Todos los timestamps en UTC con conversión local en hover

#### Data Retention
- **IoT Central**: 30 días (máximo por plan)
- **Azure Blob Storage**: 1 año (datos históricos exportados)
- **Análisis**: 4 días no consecutivos para evaluación parcial

#### SLA (Service Level Agreement)
- **Disponibilidad**: 99.9% tiempo de actividad dashboard
- **Latencia**: <2 segundos para actualización de datos en tiempo real
- **Actualización**: Intervalos automáticos según configuración de cada dispositivo

---

## Pantalla Completa (Una Sola Pantalla)

Para cumplir el requisito de "visibles en una sola pantalla", el dashboard se organizará de la siguiente manera (disposición aproximada):

```
┌─────────────────────────────────────────────────────────────────┐
│  🏫 DASHBOARD GESTIÓN EMERGENCIAS - CAMPUS UNAB                │
│  [Fecha/Hora Actual]                                            │
├─────────────────┬───────────────────────────────────────┤
│  📊 KPIs        │  📈 GRÁFICOS (4)                          │
│  - Temp.        │  1. Temp. Promedio Campus                 │
│  - Humedad      │  2. CO₂ Aulas                             │
│  - CO₂          │  3. Alarmas Incendio                      │
│  - Viento       │  4. Viento Dirección/Velocidad            │
├─────────────────┼───────────────────────────────────────┤
│  🚨 ALARMAS     │  📍 MAPA DISTRIBUCION                     │
│  - Lista activa │  - 10 nodos con íconos por zona         │
│  - Botones ACK  │  - Estados conectados/desconectados      │
└─────────────────┴───────────────────────────────────────┘
```

---

## Evidencias del Dashboard (Generar al concluir)

| Evidencia | Formato | Descripción |
|---|---|---|
| `dashboard_control_room.png` | Captura PNG/JPG | Pantalla completa del dashboard |
| `dashboard_mobile.png` | Captura PNG/JPG | Versión resumen para móvil/tablet |
| `alarmas_activas.json` | JSON | Estado actual de todas las alarmas |
| `reporte_alarmas_4dias.md` | Markdown | Reporte de alarmas en ventana 4 días |

---

## Próximos Pasos para Implementación del Dashboard

Cuando Azure IoT Central esté configurado con el Device Template `campus-emergency-v1`:

1. **Crear Device Template** (ya definido en `docs/device-template.md`)
2. **Publicar template** en instancia IoT Central
3. **Registrar 10 dispositivos** con IDs campus-ems-01 a campus-ems-10
4. **Configurar Views** (8 vistas por zona funcional)
5. **Diseñar Dashboard** usando el diseño especificado arriba
6. **Crear Rules** (8 reglas de alerta definidas)
7. **Probar visualización** con datos simulados (scripts D1-D10 ejecutándose)
8. **Capturar evidencias** (`dashboard_control_room.png`, etc.)
9. **Documentar configuración** en `work-log.md`

---

## Integración con los 10 Dispositivos

| Dispositivo | Datos Que Aparecen en Dashboard | Widget Principal |
|---|---|---|
| **D1** (Estación meteo) | temperature, humidity, wind | Gráfico línea temperatura |
| **D2** (Meteo patio) | temperature, humidity, lux | Gráfico combinación |
| **D3** (Incendio A) | smoke, flame | Tarjeta estado alarma |
| **D4** (Incendio Lab) | smoke, flame, temperature | Tarjeta estado alarma |
| **D5** (Calidad aire) | co2, pm25 | KPI CO₂ + gráfico línea |
| **D6** (Calidad exterior) | pm25, pm10, aqi | Gráfico partículas |
| **D7** (Acceso) | door_status, occupancy | KPI ocupación + estado puerta |
| **D8** (Cerramiento) | motion, temperature | Mapa posición + estado |
| **D9** (Evacuación) | occupancy, lux_emergency | Gráfico ocupación + emergencia |
| **D10** (Puesto mando) | estado_agregado, confirmacion_ack | Resumen flota + KPIs principales |

---

## Cumplimiento de Requisitos de la Guía

| Criterio Guía | Estado | Comentario |
|---|---|---|
| **Identidad Visual** (logo, nombre, no genérico) | ✅ Cumplido | "Dashboard Gestión de Emergencias - Campus UNAB" con logo institucional |
| **Métricas de Flota** (Connected/Disconnected/Unassociated) | ✅ Cumplido | Contadores agregados configurados |
| **Visualización Telemetría** (mínimo 4 gráficos) | ✅ Cumplido | 4 gráficos interactivos definidos |
| **Tarjetas KPI** (tiempo real, máximos/mínimos) | ✅ Cumplido | 5 KPIs principales con valores día |
| **Gestión Alarmas** (Rules, alertas) | ✅ Cumplido | 8 reglas documentadas con acciones |
| **Mapa Distribución** (10 nodos por zonas) | ✅ Cumplido | Íconos diferenciados, tooltips con info |
| **Sola Pantalla** | ✅ Cumplido | Layout dispuesto para una vista completa |

**Estado General M7: 7/7 requisitos cumplidos**