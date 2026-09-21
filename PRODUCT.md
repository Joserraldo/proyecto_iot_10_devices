# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static HTML/CSS/JS served by Python HTTP server (dashboard_server.py). Vanilla — no framework.

## Users

Operadores de sala de control (Campus EMS) que monitorean 10 dispositivos IoT en tiempo real y responden a alertas extremas. Situación: pantalla siempre visible en puesto de mando; respuesta esperada en segundos a minutos.

## Product Purpose

Visibilizar telemetría viva de la flota campus-ems (10 dispositivos) y permitir respuesta inmediata a alertas extremas. El operador ve el estado global, entra al detalle de cualquier dispositivo para ver histórico tipo IoT Central (gráficas, series temporales), y dispara "Llamar asesor" que envía email Brevo con la ubicación exacta de la alerta para que el asesor sepa a dónde dirigirse.

## Positioning

Único dashboard que une: (1) vista operativa tiempo real de 10 nodos heterogéneos, (2) histórico navegable por dispositivo con la misma semántica visual que IoT Central, (3) botón de acción única que dispara alerta + ubicación para despacho de asesor — todo sin salir de la herramienta ni depender del portal de Azure.

## Operating Context

- Flota: D1 meteo campus (15s), D2 meteo patio Wokwi (30s, bridge MQTT), D3 incendio Bloque A (60s), D4 incendio Lab (60s), D5 calidad aula (15s), D6 calidad exterior (300s), D7 acceso principal (30s), D8 cerramiento norte (60s), D9 evacuación pasillo (45s), D10 puesto de mando (20s).
- Telemetría llega a Azure IoT Central → dashboard la lee de logs locales (`~/iotlogs/dX.log`) con formato `[Dx] TELE {json}` en cada envío.
- Alertas extremas: temperatura >65°C, humedad <5% o >98%, PM2.5>500, AQI>350, CO>600, humo/llama=1. Anti-spam: re-notificación máx. cada 6h.
- Email Brevo configurado (api-key, sender, destinatario en `.env`).
- Puerto 8080; NSG de Azure debe permitir entrada.

## Capabilities and Constraints

- Lectura de logs cada 15s (scan background) → `/api/status` fresco.
- Histórico: últimos ~500 puntos por dispositivo en memoria (logs rotan). Persistencia no requerida para el parcial.
- Dispositivo D2 (Wokwi) solo online cuando corre la simulación.
- Botón "Llamar asesor" = dispara email inmediato con dispositivo, métrica extrema, valor, timestamp, y ubicación física del dispositivo.
- Sin auth, sin base de datos, sin WebSockets (polling 15s).

## Brand Commitments

Nombre: "Campus EMS". Voz: técnica, directa, urgencia visual sin ruido. Colores: semáforo operativo (verde/ámbar/rojo) + fondo oscuro sala de control.

## Evidence on Hand

- 10 dispositivos provisionados en IoT Central (app `6284f58c-3974-4537-9fba-a70fbb61a23a`).
- Logs locales con formato TELE unificado.
- Brevo API key funcional (mail de prueba enviado).
- Template DTDL `campus-emergency-v1` (35 campos).

## Product Principles

1. **Scanability ante todo**: el operador entiende el estado global en <2s.
2. **Acción en 1 click**: del dashboard al detalle histórico; de la alerta al despacho del asesor.
3. **Densidad informativa sin saturación**: gráficas Sparkline en grid, detalle completo al entrar.
4. **Cero dependencias externas de UI**: HTML/CSS/JS vanilla, sirve offline salvo datos.
5. **Extremos visibles, normales callados**: solo lo que rompe umbrales salta a la vista.

## Accessibility & Inclusion

WCAG AA mínimo: contraste ≥4.5:1, foco visible, navegación teclado, etiquetas ARIA en botones y gráficas. Color no es único portador de información (iconos + texto).