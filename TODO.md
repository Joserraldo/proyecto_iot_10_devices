# TODO - Proyecto IoT Central

## Estado del proyecto

- **Estado general:** Planeacion inicial
- **Escenario elegido:** 3.4 - Campus Colegio Caldas / Universidad UNAB (Gestión de Emergencias) - Seleccionado en 2026-09-19
- **Plataforma:** Azure IoT Central
- **Referencias:** `D:\José Tellez\Documents\universidad\sexto semestre\Iot_learning`
- **Ultima actualizacion:** 2026-09-18

## Reglas de colaboracion

- [ ] Cada tarea debe tener responsable, estado y criterio de aceptacion.
- [ ] Trabajar primero en un vertical slice funcional antes de crear los 10 dispositivos.
- [ ] No guardar secretos, claves, connection strings ni tokens en GitHub.
- [ ] Usar `.env.example` para documentar variables requeridas y `.env` solo localmente.
- [ ] Registrar pruebas, capturas, logs y decisiones en `docs/` o `evidencias/`.
- [ ] Actualizar este archivo despues de cada tarea terminada.
- [ ] Crear commits pequenos y descriptivos.

## Estados permitidos

- `Pendiente`
- `En progreso`
- `Bloqueada`
- `En revision`
- `Completada`

## Fase 0 - Diagnostico y alcance

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Revisar `Guia_tecnica_parcial.md` y los talleres anteriores.
  - **Aceptacion:** Se documentan patrones reutilizables de taller 2 y taller 3.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Seleccionar exactamente un escenario del parcial.
  - **Aceptacion:** El escenario tiene justificacion y cubre las zonas/variables indispensables.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Definir estructura inicial de carpetas.
  - **Aceptacion:** Cada carpeta tiene un proposito documentado en el README.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Registrar decisiones iniciales en `docs/decision-log.md`.
  - **Aceptacion:** Las decisiones de plataforma, protocolos y fuentes tienen fecha y motivo.

## Fase 1 - Arquitectura y contrato IoT

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Diseñar el catalogo de 10 dispositivos.
  - **Aceptacion:** Cada fila tiene ID, zona, origen, protocolo, intervalo, variables y responsable.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Definir Device Template de Azure IoT Central.
  - **Aceptacion:** Telemetria, propiedades, comandos, unidades, rangos y nombres estan definidos.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Definir matriz de origen de datos.
  - **Aceptacion:** Se identifican nodos Python/SDK, MQTT explicito, Wokwi local, API y replay CSV.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Definir arquitectura de 4 capas.
  - **Aceptacion:** Dispositivo, telecomunicaciones, plataforma y operacion aparecen en un diagrama.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Definir intervalos asincronos y desconexion controlada.
  - **Aceptacion:** Existen al menos 3 intervalos y un procedimiento reproducible de reconexion.

## Fase 2 - Preparacion del repositorio

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear README con instalacion, arquitectura y estado.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear `.env.example` sin valores secretos.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear `requirements.txt` o manifiesto equivalente.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Configurar `.gitignore` para `.env`, entornos virtuales, caches y logs sensibles.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear `docs/`, `evidencias/`, `python/`, `wokwi/` y `tools/` solo cuando tengan contenido real.
  - **Aceptacion:** La estructura permite que otro integrante instale y ejecute cada componente.

## Fase 3 - Vertical slice funcional

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear plantilla y primer dispositivo en Azure IoT Central.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Implementar primer nodo Python en la VM de Azure usando el SDK.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Implementar primer ESP32 en Wokwi ejecutado localmente.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Verificar DPS, MQTT/TLS, telemetria y estado `Connected`.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Verificar una propiedad writable y un comando.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Configurar una regla de alerta y guardar evidencia.
  - **Aceptacion:** Python y Wokwi publican datos visibles en IoT Central y responden a la accion definida.

## Fase 4 - Escalamiento a 10 dispositivos

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Implementar dispositivos 01-03.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Implementar dispositivos 04-06.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Implementar dispositivos 07-10.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Integrar API publica o bridge.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Integrar replay CSV/dataset historico si aplica.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Verificar que no todos los nodos dependan del mismo simulador.
  - **Aceptacion:** Existen exactamente 10 nodos registrados, con origen y comportamiento documentados.

## Fase 5 - Datos, asincronia y resiliencia

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Configurar al menos 3 intervalos de muestreo.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Ejecutar desconexion controlada de un dispositivo.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Verificar reconexion y continuidad posterior.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Preparar datos de 4 dias no consecutivos.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Calcular maximo, minimo, promedio, conteo y sumatoria cuando aplique.
  - **Aceptacion:** Logs, capturas y tablas permiten reproducir y explicar los resultados.

## Fase 6 - Control Room y documentacion

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear dashboard con identidad del escenario.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Agregar KPIs, graficos, alarmas, estados y mapa de nodos.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Completar bitacora tecnica por fecha.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Documentar instalacion local, VM de Azure y ejecucion de Wokwi.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Documentar troubleshooting y errores conocidos.
  - **Aceptacion:** Un companero puede levantar el proyecto siguiendo solo el README y los documentos enlazados.

## Fase 7 - Validacion y entrega

- [ ] **Responsable:** ____ | **Estado:** Pendiente | Ejecutar checklist de telemetria, comandos, reglas y dashboard.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Probar ejecucion simultanea desde dos equipos.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Revisar que no existan secretos ni datos sensibles.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Revisar evidencias y enlaces internos.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Crear repositorio GitHub o conectar el repositorio remoto.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Subir cambios por commits y ramas revisables.
- [ ] **Responsable:** ____ | **Estado:** Pendiente | Preparar guion de sustentacion.
  - **Aceptacion:** El proyecto puede demostrarse en vivo y el repositorio queda listo para continuidad del equipo.

## Registro de evidencias

| Fecha | Tarea | Evidencia | Ubicacion | Responsable |
|---|---|---|---|---|
| 2026-09-18 | Planning inicial | Prompt maestro y checklist creados | `Guia_tecnica_parcial.md`, `TODO.md` | José Tellez |

## Registro de bloqueos y decisiones

| Fecha | Tipo | Descripcion | Accion o responsable | Estado |
|---|---|---|---|---|
| 2026-09-18 | Decision | Wokwi se ejecutara localmente; Python operativo se ejecutara en la VM de Azure. | Equipo | Registrada |

## Checklist antes de publicar en GitHub

- [ ] README actualizado.
- [ ] `TODO.md` actualizado.
- [ ] `.env.example` incluido y `.env` excluido.
- [ ] No hay connection strings, claves, SAS tokens ni contrasenas.
- [ ] Dependencias documentadas.
- [ ] Instrucciones de ejecucion local y en VM verificadas.
- [ ] Evidencias organizadas sin secretos.
- [ ] Pruebas ejecutadas y resultados registrados.
- [ ] Commits pequenos y descriptivos.
- [ ] Companeros conocen la tarea siguiente y los bloqueos actuales.
