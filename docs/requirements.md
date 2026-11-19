# Requisitos, alcance y backlog

## Objetivo y actores
Demostrar competencias de análisis de datos, ingestión, SQL y backend Python en una solución multisectorial. Actores: visitante de portafolio, operador demo, analista e integrador técnico. La API admite credenciales por empresa con permisos read/write y RLS con una cuenta restringida. La demo web permanece separada de la API. Cada producto conserva su propia base y puede funcionar de forma independiente.

## Requisitos funcionales implementados
| ID | Requisito | Criterio de aceptación |
| --- | --- | --- |
| RF01 | Muestra autónoma | Abre sin el otro producto y muestra 24 operaciones ficticias |
| RF02 | Ingesta de eventos | Rechaza contrato o tenant inválido antes de escribir |
| RF03 | Última revisión | Un evento repetido no duplica; una revisión vieja no degrada |
| RF04 | Filtrado y métricas demo | Sector, estado, mes y texto recalculan resultados |
| RF05 | Interoperabilidad | JSON v1 válido transporta instantáneas entre productos |
| RF06 | Persistencia y autonomía API | PostgreSQL propio; arranca sin el otro producto |

## No funcionales
Validación de entradas; secretos fuera del frontend; queries parametrizadas; límites de lotes; control de organización; código separado por responsabilidad; pruebas automatizadas y build reproducible con locks; diseño responsive y etiquetas accesibles. No se han certificado un SLA, carga máxima, WCAG completa ni rendimiento de producción.

## Hoja de ruta verificable

Revisión: 2026-11-18. Las fases 1/2 están incorporadas en main ([PR #1](https://github.com/idrovodario16/nexusinsight-analytics/pull/1) y [PR #2](https://github.com/idrovodario16/nexusinsight-analytics/pull/2)), con CI aprobada. Las filas parciales no anuncian sus criterios pendientes como terminados. Una prueba omitida no satisface el criterio correspondiente.

| Prioridad | Historia | Estado observado | Terminado cuando… |
| --- | --- | --- | --- |
| P0 | Identidad de operaciones importadas | Corrección propuesta en ambos productos | UUID equivalentes no duplican filas ni métricas, se conserva la revisión mayor, empresas distintas siguen separadas y un lote inválido no modifica el estado; pruebas web y compilación aprobadas |
| P0 | Dependencias de desarrollo | Revisión 19/11: aviso GHSA-fc5q-39xc-vjpf retirado el 18/11; npm audit web sin alertas, sin cambiar paquetes | Revalidar avisos vigentes y compatibilidad antes de actualizar; conservar locks reproducibles y pruebas/build aprobados |
| P0 | Administración de empresas y usuarios | Credenciales de integración configurables; sin administración de usuarios en Insight | Gestión de credenciales y permisos por empresa con revocación probada; identidad de usuarios integrada sin acceso directo a la base de Core |
| P0 | Insight conectado al backend | Demo e ingestión API disponibles; interfaz conectada pendiente | Modos demo/API explícitos, paginación y errores visibles, E2E de consulta e ingestión contra la API de Insight |
| P0 | Identidad OIDC y RBAC | Pendiente | Operador/analista/admin autorizados por claims y tenant; pruebas de expiración y revocación aprobadas |
| P0 | Aislamiento PostgreSQL | Incorporado; RLS y credenciales por empresa | CI valida con rol restringido lecturas/escrituras cruzadas, reutilización de conexiones y rollback |
| P0 | Auditoría de actor | Inbox conserva eventos; auditoría de usuario pendiente | Ingestiones y cambios de configuración persisten actor, fecha y trazabilidad, con pruebas de cobertura y permisos |
| P1 | Módulos configurables | Pendiente | Configuración persistente por empresa; módulos deshabilitados bloqueados también en API y probados por rol |
| P1 | Configuración multisectorial | Tres sectores fijos de ejemplo | Plantillas versionadas por empresa, validación en API y migración probada sin duplicar lógica de negocio |
| P1 | Sincronización de eventos comerciales | Ingestión de operaciones y relay externo; cobertura comercial parcial | Prueba Core → Insight de venta, cobro y cancelación con reintentos, duplicados y revisiones fuera de orden, manteniendo inicio independiente |
| P1 | Copias de seguridad | Recuperación sin validar | Procedimiento documentado restaura cada base en un entorno aislado y verifica integridad, RPO y RTO medidos |
| P1 | Monitoreo del relay y servicios | Salud básica; alertas y métricas pendientes | Pruebas verifican métricas de lag, fallos, reintentos, alertas y cola de errores |
| P1 | Importación CSV analítica | Pendiente | Mapeo de columnas, validación y reporte de errores probados |
| P2 | Análisis temporal y anomalías | Pendiente | Métricas explicables verificadas contra datasets conocidos |
| P2 | Extracción de microservicios | Pendiente de necesidad demostrada | Decisión soportada por carga o autonomía de equipos |

El sistema no está completo: siguen pendientes requisitos funcionales y validaciones de seguridad, recuperación, carga y accesibilidad integral.
