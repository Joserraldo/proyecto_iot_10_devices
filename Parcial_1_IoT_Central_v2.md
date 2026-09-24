# PARCIAL 1 — Escenario IoT Central con flota heterogénea de 10 dispositivos

> Universidad Autónoma de Bucaramanga · IoT + Cloud + Sistemas Distribuidos · Parcial 1 · 2026-II

## 1. Objetivo

Diseñar, parametrizar y demostrar un escenario IoT completo sobre **Azure IoT Central**. La flota **no** se llena con un solo simulador: los 10 dispositivos se alimentan desde **códigos de envío distintos** hacia IoT Central, de modo que queden visibles la **asincronía**, las **desconexiones** y la **operación en línea** durante una ventana de al menos **4 días no continuos**.

**Producto final:**
- Un documento profesional de proyecto
- Un panel tipo cuarto de control
- Una sustentación en la que se ejecutan **dos códigos en equipos distintos**

---

## 2. Enunciado

1. Seleccionar un escenario de la sección 5.
2. Construir el **Digital Twin (Device Template)** anclado a datasheets reales.
3. Desplegar la infraestructura en IoT Central y documentar cada elemento.
4. Describir cada elemento incluyendo al menos **10 dispositivos con múltiples variables** (sensores diferentes).

Todos los grupos construyen un **catálogo único** de dispositivos cuyos **orígenes de envío** hacia IoT Central son distintos entre sí. En ese catálogo deben aparecer, entre otros: **Digital Twin / simulador nativo, Wokwi, Python, API pública, Atlas Weather** y demás orígenes justificados.

> ⚠️ Los 10 dispositivos son la suma de ese catálogo: **no** se parte la flota en bloques fijos (ni 5+5, ni "cinco obligatorios y cinco de relleno").

**En la flota debe visualizarse:**
- **Asincronía** → intervalos de muestreo distintos
- **Desconexión** → huecos en la serie, estado Disconnected
- **Operación en línea** → Connected con telemetría viva

Los gráficos cubren **4 días no continuos**. Se pueden usar plantillas o Digital Twin como referencia para generar dispositivos. Los parámetros de cada origen **—incluidos los del código—** van en las tablas de la sección 6.

**Debe realizarse:**
- El diagrama de referencia de la flota (dispositivos, telecomunicaciones e IoT Central)
- Mostrar los gráficos generados por IoT Central con el escenario elegido
- Dashboard personalizado: logo del escenario, variables, gráficos y resumen tipo **cuarto de control (control room)** para validar la información

**Última parte (presencial):** frente al ingeniero a cargo se ejecutan **dos códigos en dos equipos distintos** (p. ej. Python en un portátil y Wokwi o un puente de API en el otro). El resto de la flota puede estar histórica o en segundo plano, pero esos dos nodos deben verse **Connecting / Connected / enviando en vivo**.

---

## 3. Catálogo de orígenes de envío

Cada dispositivo declara un **origen de envío** y un **identificador de origen**. No se acepta llenar los 10 con el simulador nativo. El catálogo del grupo es **uno solo**: diez filas, diez orígenes distinguibles. Deben estar presentes los orígenes de la tabla siguiente; el resto se elige de la lista abierta al pie, u otro origen justificado, siempre que el código o el feed sea distinto.

| # | Origen | Qué es | Qué debe verse en Central |
|---|--------|--------|---------------------------|
| 1 | **Digital Twin / simulador nativo** | Dispositivo simulado sobre la plantilla (IoT Central Device Template) | Connected, telemetría periódica, propiedades editables |
| 2 | **Wokwi** | ESP32 virtual (Arduino o firmware equivalente) con sensores y, si aplica, un actuador | Alta/baja del dispositivo, 3+ variables, respuesta a un comando |
| 3 | **Python** | Script con `azure-iot-device` (DPS + MQTT o AMQP) desde laptop o VM | Envío periódico, comando o property writable, logs de sesión |
| 4 | **API pública** | Puente que consulta una API abierta (calidad de aire, ocupación, Open-Meteo, SIATA, etc.) y reenvía a Central | Valores reales o cuasi reales, marca de tiempo de la fuente y de ingestión |
| 5 | **Atlas Weather (o equivalente)** | Estación o feed meteorológico (Atlas Weather, OpenWeather, IDEAM, estación campus) | Variables meteorológicas alineadas al escenario (temp, HR, lluvia, viento, etc.) |

**Orígenes adicionales aceptados** para completar las 10 filas (cada uno cuenta si el código o el feed es otro):

- Segundo script Python con protocolo distinto
- Cliente MQTT explícito (paho / MQTT.js)
- Replay de CSV o histórico
- Segunda instancia Wokwi
- Puente HTTP/REST
- Dispositivo Plug and Play
- Segunda API pública de dominio diferente

El grupo documenta **por qué ese origen es distinto** y **cómo se provisiona**.

> **Asincronía mínima exigida:** al menos **tres intervalos de muestreo diferentes** en la flota (p. ej. 15 s, 60 s y 5 min).
>
> **Desconexión:** al menos **un dispositivo** debe mostrar un hueco documentado (apagado controlado, fallo de red o pausa del script) y la posterior **reconexión**.

---

## 4. Condiciones transversales

- **Plantilla personalizada:** logo e iconos del escenario o de la "compañía" que lo opera. Views de operador, Rules y alertas configuradas. Objetivo: un demo funcional para el cliente que lo solicitó.
- **Ventana de 4 días no continuos:** elegir cuatro fechas distintas (no tienen que ser consecutivas). Exportar o capturar gráficos de IoT Central / Data Explorer. Analizar **máximo, mínimo, promedio, recuento** y, cuando tenga sentido, **sumatoria**.
- **Datasheets:** cada variable de telemetría se ancla a un sensor o dispositivo real. En tabla: **rango del fabricante, rango operativo del escenario, unidad, precisión e intervalo de muestreo** usado en el código.
- **Arquitectura de referencia con telecomunicaciones:** capa de dispositivo, capa de red (Wi-Fi, 4G/LTE si el escenario es rural, TLS, puerto 8883 u otro justificado), capa de plataforma (DPS, IoT Central, Digital Twin) y capa de operación (Views, Rules, dashboard).
- **Documentación Microsoft:** https://docs.microsoft.com/es-es/azure/iot-central/

---

## 5. Escenarios a selección (uno por grupo)

Las tablas son una propuesta de mapeo para llegar a **10 dispositivos con variables coherentes al escenario**. El grupo arma un **solo catálogo** (inventario de 10 filas) y asigna a cada fila un **origen de envío distinto**, según la sección 3. Puede reordenar zonas y variables, siempre que respete las marcadas como **indispensables**.

### 5.1 Estadio Américo Montanini

Comprende cancha, silletería, entradas y camerinos. Objetivo de operación: **confort, aforo y condiciones de juego** visibles desde un cuarto de control el día de partido y en días de mantenimiento.

| Dev | Zona / rol | Variables sugeridas |
|-----|------------|---------------------|
| 01 | Cancha central | Temp. césped, humedad, iluminancia |
| 02 | Silletería norte | Aforo estimado, temp. ambiente, CO2 |
| 03 | Entrada principal / torniquete | Flujo, estado de puerta, temp. |
| 04 | Calidad de aire exterior | PM2.5, PM10, AQI |
| 05 | Meteorología de cubierta | Temp. ext., HR, lluvia, viento |
| 06 | Camerinos | Temp., HR, iluminancia |
| 07 | Cuarto eléctrico / UPS | Temp. tablero, humedad, estado UPS |
| 08 | Iluminación de cancha | Lux, potencia estimada, on/off |
| 09 | Acceso vehicular / parking | Ocupación, barrera abierta/cerrada |
| 10 | Zona de hidratación / concessions | Temp. nevera, puerta, HR |

> **Indispensable:** cubrir cancha, silletería, al menos una entrada y camerinos. El dashboard de partido debe permitir ver de un vistazo **clima, aforo y estado de accesos**.

### 5.2 Centro de datos

Ubicación urbana. Tres racks con temperatura y humedad por rack (indispensables). El resto de sensores cubre requisitos típicos de certificación (Uptime / TIA-942 a nivel académico): filtración de agua, humo, acceso, energía y clima exterior que condiciona el free-cooling.

| Dev | Zona / rol | Variables sugeridas |
|-----|------------|---------------------|
| 01 | Rack A | Temp. intake, temp. exhaust, HR |
| 02 | Rack B | Temp. intake, temp. exhaust, HR |
| 03 | Rack C | Temp. intake, temp. exhaust, HR |
| 04 | Pasillo frío / contención | Temp., dP entre pasillos, HR |
| 05 | Clima exterior (free-cooling) | Temp. ext., HR, radiación |
| 06 | Calidad de aire sala | PM2.5, CO2, AQI |
| 07 | Detección de agua bajo piso | Fuga (bool), humedad de piso |
| 08 | Detección de humo / incendio | Humo, temp. techo |
| 09 | PDU / energía de fila | kW, corriente, factor de potencia |
| 10 | Puerta / control de acceso | Abierta/cerrada, eventos de acceso |

> **Indispensable:** los tres racks con temperatura y humedad. El control room debe mostrar el **mapa térmico de los tres armarios** y las **alarmas de agua, humo y energía**.

### 5.3 Granja y cultivo de cacao

Predio rural. Los 10 dispositivos cubren cultivo, poscosecha, meteorología, agua y perímetro como un solo catálogo. Es indispensable medir **humedad del suelo** y **variables meteorológicas**.

| Dev | Zona / rol | Variables sugeridas |
|-----|------------|---------------------|
| 01 | Lote de cultivo 1 | Humedad de suelo, temp. suelo, EC |
| 02 | Lote de cultivo 2 | Humedad de suelo, temp. canopy |
| 03 | Lote de cultivo 3 | Humedad de suelo, iluminancia PAR |
| 04 | Dosel / sombra | Temp., HR bajo dosel, lux |
| 05 | Estación de campo | Lluvia lote, humedad foliar |
| 06 | Meteorología del predio | Temp., HR, lluvia, viento, radiación |
| 07 | Calidad de aire rural | PM2.5, HR, AQI |
| 08 | Secado / fermentación | Temp. caja, HR, masa estimada |
| 09 | Reservorio / riego | Nivel de tanque, caudal, bomba on/off |
| 10 | Perímetro / bodega | Puerta, movimiento, temp. bodega |

> **Indispensable:** humedad de suelo y un nodo meteorológico explícito. Justificar en el diagrama la salida a Internet desde zona rural (**4G/LTE, Starlink o enlace del predio**).

### 5.4 Colegio Caldas / Universidad UNAB — desastres y emergencias

El campus requiere un sistema de control de desastres y emergencias: meteorológicas, incendios, calidad del aire y seguridad perimetral. El catálogo debe incluir dispositivos de cada categoría, **sin cuotas fijas por bloque**.

| Dev | Categoría / zona | Variables sugeridas |
|-----|------------------|---------------------|
| 01 | Meteorología — estación campus | Temp., HR, lluvia, viento |
| 02 | Meteorología — patio / cubierta | Temp. superficie, lux, HR |
| 03 | Incendio — bloque A | Humo, temp. techo, flama |
| 04 | Incendio — laboratorio | Humo, temp., puerta de emergencia |
| 05 | Calidad de aire — aula | CO2, PM2.5, temp. |
| 06 | Calidad de aire — exterior | PM2.5, PM10, AQI |
| 07 | Perímetro — acceso principal | Puerta, magnetismo, ocupación |
| 08 | Perímetro — cerramiento norte | Movimiento, puerta, lux nocturno |
| 09 | Evacuación — pasillo | Ocupación, lux de emergencia, temp. |
| 10 | Puesto de mando | Estado agregado, ack de alarma |

> **Indispensable:** al menos **un nodo por categoría** (meteorología, incendio, calidad de aire, perímetro). Las **Rules** deben distinguir alerta meteorológica, incendio y perímetro; **no mezclar umbrales**.

### 5.5 Parqueo de bicicletas y patinetas UNAB

La universidad diseña estaciones de parqueo con control de seguro (abierto/cerrado), control de carga y ocupación del punto. Esas **tres variables son indispensables** en el sitio. El resto cubre clima del campus, vandalismo, energía y aforo de la estación.

| Dev | Zona / rol | Variables sugeridas |
|-----|------------|---------------------|
| 01 | Slot 1 — seguro y ocupación | Lock open/close, ocupado, temp. slot |
| 02 | Slot 2 — carga | Estado de carga, corriente, ocupado |
| 03 | Slot 3 — seguro y ocupación | Lock, ocupado, lux |
| 04 | Slot 4 — carga rápida | SoC estimado, W, temperatura conector |
| 05 | Tótem de estación — ocupación | Cupos libres, cupos totales, lock maestro |
| 06 | Clima del punto de parqueo | Temp., HR, lluvia |
| 07 | Calidad de aire del andén | PM2.5, AQI |
| 08 | Energía del tablero | kWh, corriente, estado breaker |
| 09 | Perímetro / evento | Movimiento, lux nocturno, puerta |
| 10 | Pasarela de sesión | Sesión activa, usuario anónimo, ack |

> **Indispensable:** seguro abierto/cerrado, control de carga y ocupación visibles en el control room. **Un comando remoto** debe poder abrir/cerrar un slot de demostración (Wokwi o Python).

---

## 6. Documento profesional — contenido mínimo

Formato válido para presentar el proyecto (portada, logo del escenario, historial de versiones, numeración). **No** es un informe de laboratorio de 1–2 páginas: es el **expediente del cliente**.

| Sección | Qué debe contener |
|---------|-------------------|
| **Historial de versiones** | Fecha, autor, cambio. Incluir la versión del Device Template y de cada script |
| **Arquitectura de referencia** | Diagrama de la flota completa: origen de cada dispositivo, red, DPS, IoT Central, Views/Rules. Capa de telecomunicaciones explícita |
| **Catálogo de 10 dispositivos** | Una sola tabla: ID en Central, zona, origen de envío, protocolo, intervalo, variables, datasheet citado |
| **Tablas de parámetros** | Por variable: unidad, rango datasheet, rango operativo del escenario, precisión, umbral de Rule, valor usado en el código (min/max/offset) |
| **Comparativa de variables** | Sobre los 4 días no continuos: máximo, mínimo, promedio, recuento y sumatoria cuando aplique. Relatar qué situación operativa explican esos extremos |
| **Evidencia de asincronía / desconexión** | Capturas de estado Connected/Disconnected, huecos en la serie y logs de los dos códigos que se ejecutarán en la sustentación |
| **Dashboard / control room** | Capturas del panel personalizado: logo, KPIs, gráficos, alarmas activas. El operador no programador debe entenderlo |
| **Repositorio** | README de decisiones, scripts sin secretos en claro, proyecto Wokwi, evidencias. Credenciales solo por variable de entorno o DPS attested |

---

## 7. Panel tipo cuarto de control

Además de las Views por dispositivo, el grupo construye un **dashboard de aplicación con identidad visual propia**. Mínimo visible al mismo tiempo:

- **Logo y nombre del escenario** (no el nombre genérico de la aplicación de Azure)
- **Estado de la flota:** cuántos Connected / Disconnected / Unassociated
- **Al menos cuatro gráficos de telemetría** alineados a las variables indispensables del escenario
- **KPIs numéricos** (último valor, máximo/mínimo del día seleccionado)
- **Bloque de alertas o Rules** disparadas en la ventana de 4 días
- **Un mapa o esquema de zonas** (aunque sea estático) que relacione dispositivo ↔ lugar físico

---

## 8. Sustentación presencial

Se presenta al ingeniero a cargo. Durante la evaluación el grupo:

1. Explica el escenario, el Digital Twin y el catálogo: por qué cada origen de envío es distinto.
2. Muestra el control room y navega un gráfico de los 4 días no continuos.
3. **Ejecuta dos códigos en dos equipos distintos.** Ambos deben aparecer en IoT Central y publicar al menos una variable en vivo.
4. Reproduce o explica una desconexión controlada y la reconexión de **uno de esos dos nodos**.
5. Responde por umbrales, datasheets y por las limitaciones percibidas de IoT Central.

> Si un origen (API o Atlas Weather) no puede ejecutarse en vivo por cuota o red, se muestra la **evidencia histórica** y se sustituye la ejecución en vivo por el **par Python + Wokwi**. Eso **no** exime de haber usado esos orígenes en la flota.

---

## 9. Indicadores de evaluación

| Indicador | Qué se mira | Peso |
|-----------|-------------|------|
| **IoT Template (setup + test)** | Aplicación, plantilla publicada, properties, comandos, Rules. Identidad visual del escenario | 15 % |
| **Datos, Digital Twin y arquitectura** | Catálogo de 10 dispositivos, datasheets, rangos de industria, diagrama con telecomunicaciones | 20 % |
| **Heterogeneidad de orígenes** | Orígenes distintos en el catálogo (incluye Digital Twin, Wokwi, Python, API pública, Atlas Weather) | 20 % |
| **Asincronía, desconexión y operación en línea. Ventana de 4 días y comparativa** | Gráficos no continuos. Máx / mín / promedio / recuento / sumatoria y lectura operativa de esos valores | 15 % |
| **Control room y documento** | Dashboard personalizado, tablas de parámetros (código + datasheet), historial de versiones, repo limpio | 15 % |
| **Sustentación y dos códigos en vivo** | Ejecución en dos equipos, explicación técnica y manejo de la desconexión | 15 % |

---

## 10. Recursos

- **Documentación IoT Central:** https://learn.microsoft.com/es-es/azure/iot-central/
- **Device templates, Views y Rules:** documentación vigente de la aplicación IoT Central
- **Python:** paquete `azure-iot-device` (DPS). El destino es Central, **no** un broker local
- **Wokwi ESP32 Wi-Fi:** https://docs.wokwi.com/guides/esp32-wifi — SSID `Wokwi-GUEST`
- **Feeds meteorológicos y de aire:** Atlas Weather, OpenWeather, Open-Meteo, IDEAM, SIATA u otra API pública citada
- Los **laboratorios 1–2** del curso (modelado + flota Python/Wokwi) son la base técnica de este parcial; el parcial exige **escala, heterogeneidad y documento de proyecto**.

---

*Convertido desde `Parcial_1_IoT_Central_v2.pdf` (5 páginas, UNAB · IoT + Cloud + Sistemas Distribuidos · 2026-II).*
