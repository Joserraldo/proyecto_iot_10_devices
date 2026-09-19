# Mission: Azure IoT Central - Parcial 1 - Reduced Scope

## M1: Escenario y Arquitectura Validada
### T1.1: Confirmar escenario y catálogo 10 dispositivos
- [ ] S1.1.1: Escenario Opción 3.4 (Campus UNAB - Gestión Emergencias)
- [ ] S1.1.2: Catálogo 10 dispositivos con zona, variables, origen, protocolo, intervalo

### T1.2: Validar arquitectura 4 capas
- [ ] S1.2.1: Arquitectura capa-dispositivo, capa-transporte, capa-plataforma, capa-operación
- [ ] S1.2.2: Protocolos MQTT/TLS y HTTPS por tipo de dispositivo

## M2: Device Template Contrato IoT Central
### T2.1: Template `campus-emergency-v1` verificado
- [ ] S2.1.1: Telemetría definida: temperature, humidity, co2, pm25, smoke, flame, door_status, occupancy
- [ ] S2.1.2: Propiedades writable: alert thresholds, sample interval

## M3: Repositorio y Configuración Crítica
### T3.1: Estructura Python y variables entorno
- [ ] S3.1.1: Crear scripts python/sdk_node_D1.py y python/sdk_node_D2.py con variables de entorno
- [ ] S3.1.2: Actualizar .env.example con IOT_CENTRAL_DPS_CONNECTION_STRING y SAMPLE_INTERVAL por dispositivo

### T3.2: Dependencias y gitignore
- [ ] S3.2.1: requirements.txt con azure-iot-device, paho-mqtt, requests
- [ ] S3.2.2: .gitignore configurado para .env, __pycache__, *.log

## M4: Vertical Slice - D1 y D2 Operativos
### T4.1: D1 - Estación meteo Python SDK conectado
- [ ] S4.1.1: Implementar python/sdk_node_d1.py conectado a IoT Central cada 15s
- [ ] S4.1.2: Enviar telemetría: temperature, humidity, wind_speed, wind_direction

### T4.2: D2 - Meteo patio Wokwi conectado
- [ ] S4.2.1: Configurar wokwi/d2_esp32_meteo_patio.json con sensores DHT22+BMP180
- [ ] S4.2.2: Bridge Wokwi → IoT Central con telemetría cada 30s

## M5: Escalamiento a 10 dispositivos (core only)
### T5.1: D3-D6 (Python/API devices)
- [ ] S5.1.1: D3 - Incendio Bloque A (Python SDK, 60s, smoke+flame)
- [ ] S5.1.2: D4 - Incendio Laboratorio (Python SDK, 1min, smoke+flame+temperature)
- [ ] S5.1.3: D5 - Calidad aire aula (API Pública HTTPS, 15s, co2+pm25+pm10)
- [ ] S5.1.4: D6 - Calidad aire exterior (Atlas Weather HTTPS, 5min, pm25+pm10+aqi)

### T5.2: D7-D10 (remaining devices)
- [ ] S5.2.1: D7 - Acceso principal (MQTT Explicito, 30s, door_status+occupancy)
- [ ] S5.2.2: D8 - Cerramiento norte (Replay CSV, 1min, motion+lux+temperature) con desconexión D8
- [ ] S5.2.3: D9 - Evacuación pasillo (Digital Twin, 45s, occupancy+lux_emergency+temperature)
- [ ] S5.2.4: D10 - Puesto mando (Digital Twin, 20s, estado_agregado+confirmacion_ack+temperatura_promedio)

## M6: Datos, Asincronía y Resiliencia (core)
### T6.1: Intervalos 3+ distintos verificados
- [ ] S6.1.1: Confirmar intervalos: 15s (D1,D5), 30s (D2,D7), 45s (D9), 60s (D3), 1min (D4,D8), 5min (D6), 20s (D10)

### T6.2: Desconexión D8 documentada
- [ ] S6.2.1: Procedimiento: iniciar D8 → detener MQTT → verificar Disconnected → reconexión → verificar Connected
- [ ] S6.2.2: Evidencia: timestamps desconexión y reconexión, hueco de datos ~30-45s

## M7: Control Room Dashboard (mínimo viable)
### T7.1: Dashboard con elementos mínimos
- [ ] S7.1.1: KPIs: Total Devices 10, Connected count, Disconnected count
- [ ] S7.1.2: Gráficos mínimos: temperatura, CO2, alarmas, distribución nodos

## M8: Validación y Entrega (seguridad + GitHub)
### T8.1: Checklist seguridad
- [ ] S8.1.1: Verificar sin secretos hardcodeados en todo repositorio
- [ ] S8.1.2: .env ejemplo sin valores reales, .gitignore excluye .env
- [ ] S8.1.3: requirements.txt documentado con todas las libs necesarias

### T8.2: Repositorio listo para GitHub
- [ ] S8.2.1: Commits pequeños por fase (M1, M2, M3, etc.)
- [ ] S8.2.2: Estructura visible: docs/, python/, wokwi/, data/, evidencias/