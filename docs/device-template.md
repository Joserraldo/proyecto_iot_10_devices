# Device Template Specification - Azure IoT Central

## Scenario: Campus UNAB - Gestión de Emergencias (Opción 3.4)

## Device Template: ` campus-emergency-v1`

### Telemetry (Variables enviadas por los dispositivos)

| Field Name | Units | Description | Range (Datasheet) | Operational Range | Precision |
|---|---|---|---|---|---|
| temperature | °C | Temperatura ambiente | -40 a +85 °C (sensor general) | -10 a +40 °C (campus) | ±0.5 °C |
| humidity | %HR | Humedad relativa | 0 a 100 %HR | 20 a 80 %HR | ±3 %HR |
| co2 | ppm | Concentración de CO₂ | 400 a 5000 ppm | 400 a 2000 ppm (aula) | ±50 ppm |
| pm25 | μg/m³ | Material particulado 2.5 | 0 a 500 μg/m³ | 0 a 150 μg/m³ (externo) | ±10 μg/m³ |
| pm10 | μg/m³ | Material particulado 10 | 0 a 1000 μg/m³ | 0 a 300 μg/m³ (externo) | ±15 μg/m³ |
| smoke | boolean | Detección de humo | - | - | - |
| flame | boolean | Detección de flama | - | - | - |
| wind_speed | m/s | Velocidad del viento | 0 a 150 m/s | 0 a 50 m/s (campus) | ±0.5 m/s |
| wind_direction | ° | Dirección del viento | 0 a 360° | 0 a 360° | ±5° |
| rainfall | mm | Precipitación acumulada | 0 a 200 mm/hr | 0 a 50 mm/hr | ±0.3 mm |
| lux | lux | Iluminancia | 0 a 100,000 lux | 0 a 100,000 lux | ±1% |
| co_level | ppm | Nivel de CO (monóxido de carbono) | 0 a 500 ppm | 0 a 50 ppm (alarmas) | ±5 ppm |
| door_status | boolean | Estado de puerta (abierta/cerrada) | - | - | - |
| occupancy | boolean | Nivel de ocupación | - | - | - |
| battery_level | % | Nivel de batería | 0 a 100 % | 0 a 100 % | ±2 % |
| timestamp | ISO8601 | Marca de tiempo UTC | - | - | - |

### Properties (Writable/Readable)

#### Writable Properties (Configurables desde IoT Central)

| Field Name | Units | Description | Default Value | Valid Range |
|---|---|---|---|---|
| alert_threshold_temp_max | °C | Umbral máximo de temperatura para alerta | 35.0 | 10.0 a 50.0 |
| alert_threshold_temp_min | °C | Umbral mínimo de temperatura para alerta | 15.0 | -10.0 a 40.0 |
| alert_threshold_humidity_max | %HR | Umbral máximo de humedad | 70.0 | 20.0 a 90.0 |
| alert_threshold_co2_max | ppm | Umbral máximo de CO₂ para alerta | 1500 | 400 a 5000 |
| alert_threshold_pm25_max | μg/m³ | Umbral máximo de PM2.5 | 35.0 | 0 a 100 |
| alarm_sensitivity | string | Sensibilidad de alarmas | "medium" | "low", "medium", "high" |
| sample_interval | seconds | Intervalo de muestreo (segundos) | 30 | 10 a 300 |

#### Readable Properties (Solo lectura desde IoT Central)

| Field Name | Units | Description |
|---|---|---|
| device_status | string | "Connected"/"Disconnected"/"Unassociated" |
| last_seen | ISO8601 | Última vez que se recibió telemetría |
| firmware_version | string | Versión de firmware del dispositivo |
| device_id_central | string | ID único en IoT Central |

### Commands (Acciones remotas)

| Command Name | Description | Payload | Response |
|---|---|---|---|
| `set_alert_thresholds` | Configurar umbrales de alerta desde la nube | { temp_max: float, temp_min: float, humidity_max: float, co2_max: float } | status: success/failure |
| `reboot_device` | Reiniciar dispositivo remotamente | { } | status: success/failure |
| `test_sensors` | Probar sensores del dispositivo | { sensor_list: [string] } | sensor_results: { name: string, status: pass/fail } |
| `change_interval` | Cambiar intervalo de muestreo | { interval: int } (segundos) | new_interval: int |

### Device Templates Digital Twin Relationships

Each of the 10 devices maps to a Digital Twin instance with:
- Unique device ID (format: `campus-ems-{01-10}`)
- Associated with the `campus-emergency-v1` Device Template
- Specific variable mappings per device (see Device Catalog)
- Parent-Child relationships for grouped monitoring (e.g., all weather stations roll up to "Estación meteo campus")

### Branding/Visual Customization

- **Dashboard Theme:** University colors (UNAB blue and white)
- **Custom Logo:** UNAB institutional logo
- **Device Names:** Spanish descriptive names (e.g., "Estación meteo campus", "Incendio Bloque A")
- **View Names:** Espacio, Laboratorio, Perímetro, Mando

### Rules (Alertas Preconfiguradas)

| Rule Name | Trigger Condition | Action |
|---|---|---|
| `temp_max_alert` | temperature > alert_threshold_temp_max | Enviar notificación, cambiar color tarjeta a rojo |
| `temp_min_alert` | temperature < alert_threshold_temp_min | Enviar notificación, cambiar color tarjeta a azul |
| `co2_max_alert` | co2 > alert_threshold_co2_max | Enviar notificación, activar ventilación forzada |
| `pm25_max_alert` | pm25 > alert_threshold_pm25_max | Enviar notificación, activar purificador |
| `smoke_detected` | smoke = true | Activar alarma audible, notificar bomberos |
| `flame_detected` | flame = true | Activar rociadores, evacuar área, notificar emergencias |
| `door_unauthorized` | door_status = true y fuera del horario | Bloquear acceso, notificar seguridad |
| `high_occupancy` | occupancy = true y capacidad > 80% | Controlar acceso, notificar mantenimiento |

### Versioning

- Initial version: `1.0.0` (fecha: 2026-09-18)
- Schema version: `v1`
- Breaking changes require new version and device migration
- Historic data preserved per version