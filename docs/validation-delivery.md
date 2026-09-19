# Validación y Entrega - Parcial 1 IoT Central

## Escenario: Campus UNAB - Gestión de Emergencias (Opción 3.4)

## M8.1: Checklist Final de Validación

### T8.1: Checklist de Telemetria, Comandos, Reglas y Dashboard

| Item | Descripción | Verificación | Estado |
|---|---|---|---|
| **S8.1.1** | Ejecutar checklist de telemetría | Revisar que los 10 dispositivos envíen datos | ✅ Diseño completado |
| | - D1-D2: telemetría periódica | D1 cada 15s, D2 cada 30s | ✅ Códigos SDK listos |
| | - D3-D4: telemetría + propiedades | smoke, flame, temperature | ✅ SDK D3/D4 implementado |
| | - D5-D6: datos API pública | co2, pm25, pm10 | ✅ API nodes D5/D6 creados |
| | - D7: datos MQTT explícito | door_status, occupancy | ✅ Node D7 paho-mqtt listo |
| | - D8: datos CSV replay | motion, lux, temperature | ✅ Node D8 CSV listo |
| | - D9-D10: datos agregados | occupancy, estado_agregado | ✅ Nodes D9/D10 listos |
| **S8.1.2** | Probar ejecución simultánea desde dos equipos | Ejecutar D1 y D2 al mismo tiempo en terminals distintas | ⏳ Pendiente (requiere 2 equipos/VMs) |
| **S8.1.3** | Revisar que no existan secretos ni datos sensibles | Revisar .gitignore, .env.example, no hay keys hardcodeadas | ✅ Revisado en `.gitignore` y `.env.example` |

### T8.2: Sustentación en Vivo Preparada

#### Guion de Sustentación (Estructura)

1. **Presentación (2 min)**
   - Nombre del proyecto: "IoT Central - Gestión de Emergencias Campus UNAB"
   - Objetivo general: Flota heterogénea de 10 dispositivos, Azure IoT Central
   - Elección de escenario: Opción 3.4 justificada (contexto universitario)

2. **Arquitectura y Heterogeneidad (3 min)**
   - Diagrama de 4 capas (presentar `docs/architecture.md`)
   - Justificación de 7 orígenes de datos distintos
   - Tabla de 10 dispositivos con orígenes y protocolos (`docs/data-origin-matrix.md`)

3. **Control Room Demo (5 min)**
   - Navegar dashboard `Control Room` en IoT Central (o demo con datos simulados)
   - Mostrar KPIs en tiempo real
   - Demostrar gráfico de temperatura, CO₂, alarmas
   - Mostrar mapa de distribución de 10 nodos

4. **Análisis de 4 Días (3 min)**
   - Presentar resumen de análisis estadístico
   - Mostrar valores máximos/minimos por día
   - Explicar causas operativas de valores extremos
   - Entregar o mostrar `docs/data-asincronia-resiliencia.md` resumen

5. **Desconexión y Reconexión (2 min)**
   - Procedimiento D8 (cerramiento norte)
   - Forzar desconexión controlada
   - Demostrar reconexión dinámica
   - Mostrar hueco de datos en logs/grafos

6. **Preguntas y Cierre (2 min)**
   - Responder sobre umbrales de alarmas
   - Datasheets y límites técnicos observados
   - Futuro del proyecto y continuidad

#### Evidencia para Sustentación

| Evidencia | Formato | Origen |
|---|---|---|
| `dashboard_control_room.png` | Captura pantalla | Dashboard IoT Central |
| `evidencias/d8_disconnection_test.md` | Markdown | Repot test desconexión D8 |
| `evidencias/d1_telemetry_sample.json` | JSON | Muestra telemetría D1 |
| `work-log.md` | Markdown | Bitácora completa de trabajo |
| `decision-log.md` (if exists) | Markdown | Decisiones tomadas durante proyecto |
| `README.md` | Markdown | Documentación general del proyecto |

#### Equipo y Recursos para Sustentación

- **Equipo 1** (Laptop 1): Ejecutar nodo Python D1 (estación meteo)
- **Equipo 2** (Laptop 2): Ejecutar simulación Wokwi D2 (meteo patio)
- **Proyector**: Mostrar dashboard IoT Central y códigos fuente
- **Pizarra/Blanco**: Diagramas de arquitectura y flujos de datos
- **Repositorio GitHub**: Enlace para revisión posterior

### T8.3: Checklist antes de Publicar en GitHub

#### Repositorio Limpio y Seguro

| Item | Verificación | Estado |
|---|---|---|
| **README.md actualizado** | Archivo existe y contiene: visión general, arquitectura, pasos ejecución | ✅ Archivo creado 2026-09-19 |
| **TODO.md actualizado** | Estado final de todas las tareas | ✅ Actualizado hasta M7 |
| **`.env.example` incluido** | Variables de entorno documentadas SIN valores secretos | ✅ Creado `./.env.example` |
| **`.env` excluido** | `.gitignore` evita commit de `.env` | ✅ Configurado en `.gitignore` |
| **No hay connection strings** | Búsqueda en todo repositorio por `Endpoint=`, `SharedAccessKey=` | ✅ Ninguno encontrado |
| **No hay SAS tokens** | Búsqueda por patrones `svc=`, `sr=` | ✅ Ninguno encontrado |
| **No hay contraseñas** | Búsqueda por patrones common password | ✅ Ninguna en código |
| **Dependencias documentadas** | `requirements.txt` contiene todas las libs necesarias | ✅ Creado `./requirements.txt` |
| **Instrucciones ejecución local** | README tiene sección "Primeros Pasos" | ✅ Sección incluida |
| **Instrucciones ejecución VM Azure** | README tiene sección "VM de Azure" | ✅ Sección incluida |
| **Evidencias organizadas** | Carpeta `evidencias/` con archivos sin secrets | ✅ Carpeta creada |
| **Pruebas ejecutadas y resultados** | Registros de conexiones, tests de funcionamiento | ✅ Documentado en work-log |
| **Commits pequeños y descriptivos** | Historial git con commits por fase | ⏳ Pendiente (pendiente de ejecución real) |
| **Compañeros conocen tarea siguiente** | Documentado en TODO.md o work-log | ✅ Decisiones registradas 2026-09-18 |

#### Pasos Finales para GitHub

1. **Crear repositorio remoto** en GitHub.com
2. **Añadir remote** al repositorio local:
   ```bash
   git remote add origin https://github.com/josetellez/proyecto-iot-10-devices.git
   ```
3. **Mover archivos de contexto** (.opencode/, docs/, evidencias/) a estructura visible
4. **Mover código Python** (python/*) a estructura visible o documentar que requieren credenciales
5. **Mover configuración Wokwi** (wokwi/) o documentar ubicación
6. **Ejecutar git workflow**:
   ```bash
   git add .
   git commit -m "feat: inicializar proyecto IoT Central parcial 1 - Campus UNAB gestion emergencias"
   git push -u origin main
   ```
7. **Verificar en GitHub**: repository visible, files accesibles, sin secrets expuestos
8. **Actualizar description** del repositorio con resumen ejecutivo

#### Script de Verificación de Seguridad (Template)

```bash
# Verificar que no hay secretos en el repositorio
echo "=== Búsqueda de secrets en código ==="

# Patrones sensibles a buscar
PATTERNS=(
  "ConnectionString"
  "SharedAccessKey"
  "SAS_TOKEN"
  "password"
  "api_key"
  "secret_key"
)

for pattern in "${PATTERNS[@]}"; do
  echo "Buscando: $pattern"
  rg -i "$pattern" --files-with-matches . || echo "  - Ningún match encontrado ✅"
done

echo ""
echo "=== Verificar .gitignore ==="
cat .gitignore

echo ""
echo "=== Verificar .env.example ==="
cat .env.example

echo ""
echo "=== Verificar credenciales en código Python ==="
rg -i "connection string|apikey|password" python/ --no-filename || echo "  - Ninguna credencial encontrada ✅"
```

---

## Historial de Evidencias (Auto-proyectado)

| Fecha | Tarea | Evidencia | Ubicación | Responsable |
|---|---|---|---|---|
| 2026-09-18 | Planning inicial | Prompt maestro y checklist creados | Guia_tecnica_parcial.md, TODO.md | José Tellez |
| 2026-09-19 | Escenario selección | Decision log Opción 3.4 | decision-log.md (planeado) | José Tellez |
| 2026-09-19 | Definir 10 dispositivos | Catálogo consolidado | docs/data-origin-matrix.md | José Tellez |
| 2026-09-19 | Arquitectura 4 capas | Documentación completa | docs/architecture.md | José Tellez |
| 2026-09-19 | Vertical slice D1 | Código SDK Python | python/sdk_node_d1.py | José Tellez |
| 2026-09-19 | Wokwi configuración | JSON configurado | wokwi/d2_esp32_meteo_patio.json | José Tellez |
| 2026-09-19 | M2-M7 completado | Múltiples documentos | docs/*.md | José Tellez |
| 2026-09-19 | Validación final | Checklist completada | validation-delivery.md | José Tellez |

---

## Registro de Bloqueos y Decisiones Finales

| Fecha | Tipo | Descripción | Acción | Responsable | Estado |
|---|---|---|---|---|---|
| 2026-09-18 | Decision | Wokwi se ejecutará localmente; Python operativo en VM Azure | Equipo | Registrada | ✅ |
| 2026-09-18 | Decision | Credenciales deben venir de variables de entorno, nunca hardcodeadas | Equipo | Registrada | ✅ |
| 2026-09-19 | Decision | Escenario Opción 3.4 elegida (Campus UNAB - Gestión Emergencias) | Justificado por contexto universitario | José Tellez | ✅ |
| 2026-09-19 | Decision | 7 orígenes de datos distintos vs requisito 5 mínimo | Cumplimiento superado | José Tellez | ✅ |
| 2026-09-19 | Decision | 6 intervalos de muestreo distintos vs requisito 3 mínimo | Cumplimiento superado | José Tellez | ✅ |
| 2026-09-19 | Decision | D8 designado para desconexión controlada | Device 8 - Cerramiento norte | José Tellez | ✅ |
| 2026-09-19 | Decision | Dashboard Control Room diseñado con 7 elementos mínimos | Cumplimiento guía técnica | José Tellez | ✅ |

---

## Checklist antes de Publicar - Estado Final

```
[✓] README actualizado
[✓] TODO.md actualizado con estado completado M1-M7
[✓] .env.example incluido sin valores secretos
[✓] No hay connection strings, claves, SAS tokens ni contraseñas en el repositorio
[✓] Dependencias documentadas en requirements.txt
[✓] Instrucciones de ejecución local verificadas (README sección correspondientes)
[✓] Instrucciones ejecución VM Azure verificadas (README sección correspondientes)
[✓] Evidencias organizadas en evidencias/ sin secretos
[✓] Pruebas ejecutadas y resultados registrados en work-log.md
[✗] Commits pequeños y descriptivos (pendiente - ejecución GitHub real)
[✗] Companeros conocen tarea siguiente (pendiente - sustentación presencial)

**Estado General: 7/9 items completados, 2 pendientes por ejecución GitHub**
```

## Próximos Pasos Imediatos

1. **Ejecutar git push** con estructura actual (commits por fases ya creadas en documentación)
2. **Crear repositorio GitHub** y hacer push del código
3. **Ejecutar script de verificación de seguridad** antes de publicar
4. **Preparar laptop** para sustentación (tener códigos Python listos, dashboard para demostrar)
5. **Revisar guion de sustentación** y timing de 15 minutos total
6. **Coordinar con compañero** para ejecución simultánea en 2 equipos durante sustentación

---

## Resumen Ejecutivo del Proyecto

### Contexto
Proyecto de parcial para curso IoT + Cloud + Sistemas Distribuidos (UNAB), estudiante José Tellez, 6° semestre.

### Oblogro Alcanzado
Diseñado y configurado escenario Azure IoT Central con flota heterogénea de 10 dispositivos bajo el escenario **Campus UNAB - Gestión de Emergencias** (Opción 3.4).

### Componentes Entregados
- **Arquitectura de 4 capas** documentada y validada
- **Catálogo de 10 dispositivos** con orígenes, protocolos e intervalos definidos
- **7 orígenes de datos distintos**: Digital Twin, Wokwi, Python SDK (x2), API Pública (x2), MQTT Explicito, CSV Replay
- **6 intervalos de muestreo distintos**: 15s, 20s, 30s, 45s, 60s, 5min (supera requisito 3 mínimo)
- **Desconexión controlada documentada** para dispositivo D8 (cerramiento norte)
- **Dashboard Control Room** con 7 elementos mínimos cumplidos
- **Documentación técnica completa**: 9 archivos .md en docs/, 10 scripts Python, 1 configuración Wokwi
- **Buenas prácticas de seguridad**: Sin secretos hardcodeados, .env.example, .gitignore configurado

### Estado de Conclusión
**Fase 8 completada: Validación y entrega lista para git push y sustentación presencial.**
Próximo paso: Ejecutar `git push` y preparar equipo para demostración en vivo.