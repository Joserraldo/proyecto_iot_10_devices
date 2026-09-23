# BITÁCORA DE SESIÓN — parcial proyecto IoT
## Fecha: 2026-09-23
## Responsable: José Tellez + Asistente IA

---

## 1. PROBLEMA REPORTADO

> "La página está muy pesada, no carga, se pausó sola — creo que es porque pide todo el tiempo datos aunque no se lo pida."

**Causa raíz identificada:** El dashboard pollingaba el histórico completo de cada dispositivo cada 30 segundos (por cada dispositivo abierto en el popup). Con 10 dispositivos × historial × polling constante = saturación de red/VM.

---

## 2. ARQUITECTURA ANTERIOR (problemática)

```
 каждые 30s → GET /api/history?id=01&range=24h&max=2000
 cada dispositivo abierto → request independiente
 → histórico se recarga aunque nada haya cambiado
 → popup lento / VM saturada
```

---

## 3. SOLUCIÓN IMPLEMENTADA

### 3.1 Carga a demanda (lazy on-demand)
- La página principal (/) carga solo estado vivo + KPIs, **sin pedir histórico**.
- Al abrir un dispositivo (popup modal o /chart/ID): **1 solo request** trae todo el histórico.
- El histórico **nunca se vuelve a pedir** mientras el popup esté abierto.
- Solo estado y logs se refrescan cada 30s.
- Botón "Actualizar histórico" para forzar re-lectura manual.

### 3.2 Navegación temporal en popup modal (nuevo)
- Botones de rango: **1h / 6h / 24h / 72h / 7d / todo** → zoom sobre la ventana ya cargada.
- ◀ ▶ (prev/next): mueve hacia atrás/adelante día a día sin recargar datos.
- Arrastrar con mouse sobre la gráfica → mueve la ventana temporal.
- Ctrl + rueda del mouse → zoom in/out centrado en el cursor.
- Campo datetime-local → salto directo a fecha/hora.
- Navegación opera 100% sobre `state.view` (JavaScript), sin nuevos requests.

### 3.3 Página standalone /chart/ID mejorada
- Mismas herramientas de navegación (rango, prev/next, drag, ctrl+wheel, jump).
- Downsample inteligente en servidor: conserva picos, hasta 2500 puntos.
- Info de "X de Y puntos (picos conservados)" visible en la UI.

---

## 4. VERIFICACIÓN END-TO-END (con datos reales)

### Test: popup abre y navega sin re-pedir histórico
```
popup abierta → history requests: +1 (solo la primera vez)
después de 6s idle → history requests: +0 (0 = no se vuelve a pedir) ✓
```

### Test: rango 1h / prev / next / jump
```
ventana inicial: 21/9/2026, 21:38:31 -> 23:39:31 (2h de datos reales)
rango 1h → se muestra la ventana de 1h centrada en los datos disponibles
prev x2 → retrocede en el tiempo (sin re-request)
next → avanza
jump a 2026-09-21T04:00 → mueve la ventana correctamente
```

### Test: no errores JS
```
main dashboard: 0 errores JS ✓
chart page: 0 errores JS ✓
popup modal: 0 errores JS ✓
```

### Test: navegación standalone /chart/ID
```
rango 1h → view cambia correctamente
prev → view retrocede correctamente
chart dibujar: true ✓
```

---

## 5. ARCHIVOS MODIFICADOS

| Archivo | Cambio |
|---------|--------|
| `python/dashboard_server_v2.py` |Rediseño de carga de histórico: 1 request on-demand, navegación temporal propia (sin chartjs-plugin-zoom), prev/next/drag/ctrl+wheel operativos |
| `python/mqtt_bridge_wokwi.py` | Limpieza menor |
| `wokwi/wokwi.ino` | Código ESP32 actualizado |
| `ops/*.sh` | Scripts de despliegue systemd |

---

## 6. CAPTURAS NECESARIAS PARA EL INFORME DEL PARCIAL

### Captura 1 — Dashboard principal (página de entrada)
- URL: `https://parcialiot-jose-juancho.duckdns.org/`
- Qué mostrar: las 10 tarjetas de dispositivos con estado vivo y KPIs
- Evidencia de: los 10 dispositivos funcionando

### Captura 2 — Popup/modal de un dispositivo con histórica
- URL: `https://parcialiot-jose-juancho.duckdns.org/`
- Acción: hacer clic en cualquier tarjeta
- Qué mostrar: popup con gráfica temporal, rango, prev/next, stats, logs
- Evidencia de: navegación temporal, datos históricos cargados

### Captura 3 — Navegación de rango (1h / 6h / 24h / 7d)
- Mostrar cómo los botones de rango hacen zoom sin recargar datos
- Evidencia de: la gráfica cambia de escala sin nuevos requests

### Captura 4 — Navegación prev/next (mover en el tiempo)
- Mostrar ◀ ▶ funcionando para moverse hacia atrás sin recargar
- Evidencia de: scroll temporal sobre datos ya cargados

### Captura 5 — Campo jump (fecha/hora)
- Mostrar que se puede escribir una fecha y la gráfica salta ahí
- Evidencia de: acceso directo a cualquier momento del histórico

### Captura 6 — Página standalone /chart/ID
- URL: `https://parcialiot-jose-juancho.duckdns.org/chart/01`
- Qué mostrar: métrica ampliada con toolbar de navegación
- Evidencia de: página alternativa con las mismas herramientas

### Captura 7 — Log del dispositivo en vivo
- Mostrar la sección de logs en el popup o en /chart/ID
- Evidencia de: streaming de eventos en tiempo real

### Captura 8 — Consola de red del navegador (DevTools)
- Pestaña Network filtrada por `/api/` mientras se navega el popup
- Mostrar que history se pidió 1 vez (al abrir) y nunca más
- Evidencia de: polling eliminado, carga a demanda

### Captura 9 — Azure IoT Central (portal)
- Devices → estado Connected, telemetry fluyendo
- Evidencia de: los 10 dispositivos enviando datos a la nube

### Captura 10 — Wokwi (simulador ESP32)
- Captura del simulador con laograma del ESP32 y serial monitor
- Evidencia de: el código firmware corriendo

---

## 7. EVIDENCIAS DE ÉXITO (resultados verificados)

- [x] `selftest OK` — el servidor pasa todas las pruebas internas
- [x] 0 history re-requests después de abrir el popup
- [x] Rango 1h/6h/24h hace zoom sobre la ventana ya cargada
- [x] prev/next navega sin recargar
- [x] drag y ctrl+wheel operan sobre state.view (no recargan)
- [x] jump a fecha funciona
- [x] 0 errores JS en todas las páginas
- [x] 10 tarjetas visibles en dashboard principal
- [x] Chart.js carga correctamente con adaptador de fechas

---

## 8. DEPLOY EN LA VM

Para que los cambios estén en producción en `https://parcialiot-jose-juancho.duckdns.org/`:

```bash
# Desde la VM o por SSH:
sudo systemctl restart campus-ems
# o si no hay systemd:
cd /opt/campus-ems && python dashboard_server_v2.py &
```

El archivo actualizado necesita estar en la ruta del servicio en la VM.