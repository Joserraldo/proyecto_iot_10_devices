# Guía Técnica / Prompt de Requerimientos: Parcial 1 - IoT Central (Flota Heterogénea)

**Curso:** IoT + Cloud + Sistemas Distribuidos (UNAB)  
**Proyecto:** Parcial 1 - Escenario IoT Central con flota heterogénea de 10 dispositivos  
**Objetivo para la IA / Desarrollador:** Diseñar, parametrizar, simular, documentar y sustentante un escenario de IoT sobre **Azure IoT Central** con 10 dispositivos heterogéneos, diferentes orígenes de datos, asincronía y operación histórica/en vivo.

---

## 1. Resumen Ejecutivo de Requerimientos
Para considerar completado el parcial, se debe generar y entregar:
1. **Selección de 1 Escenario:** Elegir una de las 5 opciones descritas en la Sección 3.
2. **Device Template (Digital Twin):** Configurado con variables ancladas a datasheets reales.
3. **Flota Heterogénea de 10 Dispositivos:** Inventario exacto de 10 nodos con al menos 5 orígenes de envío distintos (sin repetir simulador nativo para todos).
4. **Comportamiento Temporal:** Visualización de **4 días no continuos** de datos con asincronía, desconexiones controladas y telemetría viva.
5. **Dashboard Tipo Cuarto de Control (Control Room):** Personalizado con la marca del escenario, KPIs, gráficos, mapa visual y estado de la flota.
6. **Documento Técnico de Proyecto:** Documento estructurado tipo expediente de cliente con historial, arquitectura, catálogo, parámetros y métricas.
7. **Sustentación en Vivo:** Código funcionando en **dos equipos distintos** en tiempo real.

---

## 2. Catálogo de Orígenes de Datos (10 Dispositivos)

Se debe construir **un catálogo único de 10 filas/dispositivos**. Cada dispositivo debe pertenecer al escenario elegido y utilizar un origen de envío distinto o debidamente justificado.

### Orígenes Obligatorios en la Flota:
| # | Origen | Definición Técnica | Requisito en Azure IoT Central |
|---|---|---|---|
| **1** | **Digital Twin / Simulador Nativo** | Dispositivo simulado internamente desde la plantilla (*Device Template*) de IoT Central. | Estado `Connected`, telemetría periódica y propiedades editables. |
| **2** | **Wokwi** | ESP32 virtual (Arduino/ESP-IDF) simulando sensores y al menos 1 actuador respondiendo a comandos. | Alta/baja del nodo, $\ge 3$ variables, ejecución de comandos remotos. |
| **3** | **Python Script** | Script local/VM ejecutando el SDK `azure-iot-device` (vía DPS + MQTT/AMQP). | Envío periódico, comando/property *writable*, logs de consola local. |
| **4** | **API Pública (Bridge)** | Middleware/script puente que consume una API pública real (ej. Open-Meteo, SIATA, Calidad de Aire) y reenvía a Central. | Datos reales/cuasi reales, marcas de tiempo de fuente e ingestión. |
| **5** | **Atlas Weather / Feed Meteo** | Estación o feed meteorológico (OpenWeather, IDEAM, Atlas Weather, campus). | Variables meteorológicas alineadas al contexto del escenario. |

### Orígenes Adicionales Aceptados (para completar los 10 nodos):
* Segundo script Python con protocolo o estructura distinta.
* Cliente MQTT explícito (Paho / MQTT.js).
* Replay de datos desde CSV / Dataset histórico.
* Segunda instancia de Wokwi con otra lógica/sensores.
* Puente HTTP / REST API.
* Dispositivo IoT Plug and Play.
* Segunda API pública de dominio distinto.

### Requisitos de Dinámica de Red:
* **Asincronía mínima:** Al menos **3 intervalos de muestreo diferentes** en la flota (ejemplos: $15\text{ s}$, $60\text{ s}$, $5\text{ min}$).
* **Desconexión:** Al menos **1 dispositivo** debe presentar un hueco de datos documentado (apagado programado o fallo de red) y su posterior reconexión (`Disconnected` $\rightarrow$ `Connected`).

---

## 3. Escenarios Posibles (Seleccionar EXACTAMENTE 1)

El grupo o la IA debe elegir uno de los siguientes contextos y mapear sus 10 dispositivos respetando las zonas y variables indispensables:

### Opcion 3.1: Estadio Américo Montanini
* **Objetivo:** Confort, aforo y condiciones de juego en días de partido y mantenimiento.
* **Indispensable:** Cubrir cancha, silletería, al menos 1 entrada y camerinos.
* **Mapeo de Nodos (01 al 10):**
  1. *Cancha central:* Temp. césped, humedad, iluminancia.
  2. *Silletería norte:* Aforo estimado, temp. ambiente, $\text{CO}_2$.
  3. *Entrada principal / torniquete:* Flujo de personas, estado de puerta, temp.
  4. *Calidad de aire exterior:* $\text{PM2.5}$, $\text{PM10}$, AQI.
  5. *Meteorología de cubierta:* Temp. ext., HR, lluvia, viento.
  6. *Camerinos:* Temp., HR, iluminancia.
  7. *Cuarto eléctrico / UPS:* Temp. tablero, humedad, estado UPS.
  8. *Iluminación de cancha:* Lux, potencia estimada, estado On/Off.
  9. *Acceso vehicular / Parking:* Ocupación, barrera abierta/cerrada.
  10. *Zona de hidratación / Concessions:* Temp. neveras, estado puerta, HR.

### Opción 3.2: Centro de Datos (Data Center)
* **Objetivo:** Monitoreo Uptime / TIA-942 (racks, energía, incendios, agua).
* **Indispensable:** Los 3 racks con temperatura y humedad individual.
* **Mapeo de Nodos (01 al 10):**
  1. *Rack A:* Temp. intake, temp. exhaust, HR.
  2. *Rack B:* Temp. intake, temp. exhaust, HR.
  3. *Rack C:* Temp. intake, temp. exhaust, HR.
  4. *Pasillo frío / Contención:* Temp., diferencial de presión ($\text{dP}$), HR.
  5. *Clima exterior (Free-cooling):* Temp. ext., HR, radiación solar.
  6. *Calidad de aire en sala:* $\text{PM2.5}$, $\text{CO}_2$, AQI.
  7. *Detección de agua bajo piso:* Estado de fuga (booleano), humedad de piso.
  8. *Detección de humo / Incendio:* Detección de humo, temp. en techo.
  9. *PDU / Energía de fila:* Potencia ($\text{kW}$), corriente, factor de potencia.
  10. *Control de acceso / Puerta:* Estado abierta/cerrada, eventos de acceso.

### Opción 3.3: Granja y Cultivo de Cacao
* **Objetivo:** Cultivo rural, poscosecha, meteorología y perímetro.
* **Indispensable:** Humedad de suelo y un nodo meteorológico explícito. Justificar telecomunicaciones rurales (4G/LTE, Starlink, etc.).
* **Mapeo de Nodos (01 al 10):**
  1. *Lote de cultivo 1:* Humedad de suelo, temp. suelo, electroconductividad (EC).
  2. *Lote de cultivo 2:* Humedad de suelo, temp. del dosel vegetal.
  3. *Lote de cultivo 3:* Humedad de suelo, iluminancia PAR.
  4. *Dosel / Sombra:* Temp., HR bajo dosel, lux.
  5. *Estación de campo:* Lluvia por lote, humedad foliar.
  6. *Meteorología del predio:* Temp., HR, lluvia, viento, radiación.
  7. *Calidad de aire rural:* $\text{PM2.5}$, HR, AQI.
  8. *Secado / Fermentación:* Temp. de caja, HR, masa estimada.
  9. *Reservorio / Riego:* Nivel de tanque, caudal, estado bomba On/Off.
  10. *Perímetro / Bodega:* Estado puerta, sensor de movimiento, temp. bodega.

### Opción 3.4: Campus Colegio Caldas / Universidad UNAB (Gestión de Emergencias)
* **Objetivo:** Control de emergencias meteorológicas, incendios, calidad de aire y perímetro.
* **Indispensable:** Al menos 1 nodo por categoría. Rules diferenciadas por tipo de alerta.
* **Mapeo de Nodos (01 al 10):**
  1. *Estación meteo campus:* Temp., HR, lluvia, viento.
  2. *Meteo patio / cubierta:* Temp. superficie, lux, HR.
  3. *Incendio Bloque A:* Humo, temp. techo, sensor de flama.
  4. *Incendio Laboratorio:* Humo, temp., puerta de emergencia.
  5. *Calidad de aire en aula:* $\text{CO}_2$, $\text{PM2.5}$, temp.
  6. *Calidad de aire exterior:* $\text{PM2.5}$, $\text{PM10}$, AQI.
  7. *Acceso principal / Perímetro:* Puerta, sensor magnético, ocupación.
  8. *Cerramiento norte:* Movimiento, puerta, lux nocturno.
  9. *Evacuación pasillo:* Ocupación, lux de emergencia, temp.
  10. *Puesto de mando:* Estado agregado, confirmación de alarma (*ACK*).

### Opción 3.5: Parqueo de Bicicletas y Patinetas UNAB
* **Objetivo:** Estaciones de micro-movilidad, seguros, carga y aforo.
* **Indispensable:** Estado de seguro (lock), control de carga y ocupación del punto. Comando para abrir/cerrar seguro de prueba.
* **Mapeo de Nodos (01 al 10):**
  1. *Slot 1 (Seguro y ocupación):* Estado de seguro, ocupación, temp. slot.
  2. *Slot 2 (Carga estándar):* Estado de carga, corriente, ocupación.
  3. *Slot 3 (Seguro y ocupación):* Estado de seguro, ocupación, lux.
  4. *Slot 4 (Carga rápida):* Estado de carga ($\text{SoC}$), potencia ($\text{W}$), temp. conector.
  5. *Tótem de estación:* Cupos libres, cupos totales, seguro maestro.
  6. *Clima del punto:* Temp., HR, lluvia.
  7. *Calidad de aire andén:* $\text{PM2.5}$, AQI.
  8. *Energía del tablero:* Consumo ($\text{kWh}$), corriente, estado del breaker.
  9. *Perímetro / Evento:* Movimiento, lux nocturno, estado puerta.
  10. *Pasarela de sesión:* Sesión activa, usuario anónimo, confirmación (*ACK*).

---

## 4. Estructura del Documento Final a Entregar

El entregable escrito debe redactarse con formato de expediente/propuesta técnica profesional e incluir:

1. **Historial de Versiones:** Registro formal de cambios (fecha, autor, versión del Device Template y scripts).
2. **Arquitectura de Referencia:** Diagrama visual con 4 capas explícitas:
   * *Capa Dispositivo:* Tipos de nodos y orígenes.
   * *Capa Telecomunicaciones:* Protocolos, puertos (ej. MQTT/TLS 8883), redes (Wi-Fi, 4G, Starlink).
   * *Capa Plataforma:* DPS, IoT Central, Device Templates.
   * *Capa Operación:* Views, Rules, Dashboard.
3. **Catálogo de 10 Dispositivos:** Tabla consolidadora (ID en Central, zona, origen de envío, protocolo, intervalo de muestreo, variables, datasheets citados).
4. **Tabla de Parametrización Técnica:** Por cada variable de cada dispositivo incluir:
   * Unidad de medida.
   * Rango real del datasheet del fabricante.
   * Rango operativo en el escenario.
   * Precisión del sensor.
   * Umbral configurado en las *Rules*.
   * Valores min/max/offset implementados en código.
5. **Análisis Estadístico (4 Días No Continuos):**
   * Evaluación de 4 fechas no consecutivas extraídas de Azure IoT Central / Data Explorer.
   * Cálculo de: Máximo, Mínimo, Promedio, Recuento de mensajes y Sumatoria (si aplica).
   * Explicación cualitativa/operativa de la causa de cada valor extremo observado.
6. **Evidencia de Asincronía y Desconexiones:**
   * Muestras visuales de estados `Connected` / `Disconnected`.
   * Gráficos con huecos de datos por desconexión y logs de ejecución local.
7. **Diseño del Control Room:** Capturas de pantalla comentadas del dashboard.
8. **Repositorio:** Enlace a repositorio con código limpio (credenciales por variables de entorno o DPS, sin secretos explícitos).
9. **Ejemplos de trabajos anteriores:** Se pueden consultar ejemplos de trabajos previos relacionados en `D:\José Tellez\Documents\universidad\sexto semestre\Iot_learning`.

---

## 5. Especificaciones del Dashboard (Cuarto de Control)

El panel interactivo en IoT Central debe cumplir los siguientes elementos mínimos visibles en una sola pantalla:
* **Identidad Visual:** Branding del escenario (logo personalizado, nombre formal del proyecto, no el nombre genérico de la app).
* **Métricas de Flota:** Contadores agregados con estados (`Connected`, `Disconnected`, `Unassociated`).
* **Visualización de Telemetría:** Al menos 4 gráficos interactivos alineados con las variables indispensables del escenario.
* **Tarjetas KPI:** Valores en tiempo real (última lectura, máximos y mínimos del día).
* **Gestión de Alarmas:** Módulo de reglas (*Rules*) y alertas disparadas durante la ventana evaluada.
* **Mapa de Distribución:** Esquema/mapa de localización física de los 10 nodos por zonas.

---

## 6. Criterios y Rúbrica de Evaluación

| Criterio | Descripción del Indicador | Ponderación |
|---|---|---|
| **IoT Template & Configuración** | Device template publicado correctamente, propiedades, comandos, reglas y personalización gráfica del entorno. | **15%** |
| **Digital Twin & Arquitectura** | Catálogo técnico de 10 dispositivos, fichas técnicas (datasheets), rangos operativos y diagrama de arquitectura con telecomunicaciones. | **20%** |
| **Heterogeneidad de Orígenes** | Diversidad de fuentes (Digital Twin, Wokwi, Python, APIs, Atlas Weather). Evidencia de asincronía, desconexión y datos en vivo. | **20%** |
| **Análisis de 4 Días & Métricas** | Análisis de la ventana de datos no continua, cálculo e interpretación operativa de métricas (Máx, Min, Prom, Count, Suma). | **15%** |
| **Control Room & Documento** | Calidad del informe profesional, dashboard claro e intuitivo para operaciones, repositorio ordenado y seguro. | **15%** |
| **Sustentación & Código en Vivo** | Demostración presencial, ejecución simultánea en 2 equipos distintos, explicación técnica y manejo de desconexión/reconexión. | **15%** |

---

## 7. Protocolo para la Sustentación Presencial
Durante la evaluación con el evaluador/docente, el equipo debe:
1. Presentar la arquitectura del escenario y explicar la justificación de heterogeneidad del catálogo.
2. Navegar el *Control Room* y analizar las métricas en los gráficos de 4 días.
3. **Ejecución simultánea en vivo:** Iniciar transmisiones desde 2 computadores independientes (ej. Script Python en Laptop 1 y Wokwi/API Bridge en Laptop 2). Ambos deben registrar telemetría activa en tiempo real.
4. Forzar/explicar una **desconexión controlada** en uno de los nodos activos y demostrar su reconexión dinámica.
5. Responder preguntas sobre umbrales de alarmas, datasheets y límites técnicos observados en Azure IoT Central.

---

## 8. Prompt Maestro para el Planning y la Implementación

Usar el siguiente prompt para iniciar el trabajo en este repositorio. El prompt indica a la IA que debe estudiar primero los trabajos anteriores y reutilizar sus patrones antes de proponer código nuevo:

```text
Actúa como líder técnico y compañero de equipo para desarrollar este proyecto de IoT de forma incremental y documentada.

Contexto del proyecto:
- El proyecto actual está en: D:\José Tellez\Documents\universidad\sexto semestre\proyecto_iot_10_devices
- Existen trabajos anteriores de referencia en: D:\José Tellez\Documents\universidad\sexto semestre\Iot_learning
- Revisa primero el README principal y los talleres anteriores, especialmente taller_2_iot y taller_3_iot.
- Toma como referencia su estructura de README, bitácoras, evidencias, variables de entorno, Python en VM de Azure, Azure IoT Central, DPS, MQTT/TLS y cliente MQTT explícito con paho-mqtt.
- No copies secretos, credenciales, IPs temporales ni configuraciones específicas que no correspondan a este proyecto.

Objetivo:
Construir el parcial de Azure IoT Central con un escenario de 10 dispositivos heterogéneos, telemetría histórica y en vivo, asincronía, desconexión/reconexión, dashboard tipo Control Room y documentación suficiente para que otros compañeros puedan continuar el trabajo.

Arquitectura y restricciones técnicas:
- Azure IoT Central será la plataforma central.
- La VM de Azure ejecutará los nodos Python que deban operar remotamente.
- Wokwi se ejecutará localmente para simular el ESP32; no asumir que Wokwi corre dentro de la VM.
- MQTT sobre TLS y DPS deben documentarse claramente.
- Usar el SDK de Azure cuando simplifique un nodo operativo.
- Usar MQTT explícito con paho-mqtt cuando se necesite visibilidad del protocolo, mediciones o un bridge.
- Todas las credenciales deben venir de variables de entorno y nunca deben entrar al repositorio.
- Mantener compatibilidad con Windows/local y Linux/VM cuando sea razonable.

Forma de trabajo obligatoria:
1. Inspecciona el repositorio actual y los ejemplos anteriores antes de editar.
2. Propón un plan pequeño, ordenado por dependencias y con criterios verificables.
3. No implementes los 10 dispositivos de una sola vez. Empieza con un vertical slice funcional: plantilla, un nodo Python, un dispositivo Wokwi, telemetría, una regla y evidencia.
4. Después de cada cambio ejecuta la validación más cercana disponible y registra el resultado en la bitácora.
5. Antes de añadir una dependencia o una arquitectura nueva, explica por qué no basta reutilizar el patrón de los talleres.
6. Actualiza README, bitácora, evidencias, .env.example y TODO.md conforme avance el trabajo.
7. Usa commits pequeños y descriptivos para que el equipo pueda revisar o continuar cada etapa.

Entregables iniciales del planning:
- Crear o actualizar TODO.md con checklist por fases, responsables, dependencias, estado y criterio de aceptación.
- Definir la estructura de carpetas del proyecto y el propósito de cada carpeta.
- Elegir exactamente un escenario y justificarlo.
- Diseñar el catálogo de los 10 dispositivos, sus variables, origen, protocolo, intervalo y zona.
- Definir la plantilla de IoT Central y el contrato de telemetría, propiedades y comandos.
- Definir qué nodos usarán SDK Python, MQTT explícito, Wokwi local, API pública, replay CSV y otros orígenes.
- Definir la estrategia de datos de 4 días no consecutivos y cómo se generará o conservará la evidencia.
- Definir las pruebas de conexión, telemetría, comandos, alertas, asincronía y desconexión/reconexión.
- Definir la documentación necesaria para que otro integrante pueda instalar, configurar, ejecutar y verificar el proyecto.

Formato de cada respuesta de trabajo:
- Objetivo de la tarea.
- Archivos que se crearán o modificarán.
- Dependencias y prerequisitos.
- Implementación mínima propuesta.
- Comando o prueba de validación.
- Evidencia que debe guardarse.
- Estado y siguiente tarea en TODO.md.

Comienza ahora con un diagnóstico breve del repositorio y una propuesta de planning. No escribas código de los 10 dispositivos hasta que el catálogo, la plantilla y el primer vertical slice estén definidos.
```

Este prompt debe usarse junto con `TODO.md`, que será la fuente visible del estado del proyecto y facilitará la continuidad entre integrantes del equipo.
