# Estrategia de pruebas

1. Modelo de demo: muestras válidas, rechazo atómico de eventos inválidos, reenvíos y revisiones fuera de orden, reglas de estados e indicadores sobre conjunto vacío. `tests/import-identity.test.mjs` verifica UUID en mayúsculas/minúsculas, coincidencia de empresa en sobre/datos, reconciliación de registros existentes conservando la revisión mayor, métricas sin duplicados, empresas distintas y entradas originales sin modificar. Las nuevas regresiones fallaron antes de la corrección.
   `tests/import-timezones.test.mjs` verifica UTC y offsets en los tres campos temporales, conservación exacta del texto, rechazo de lotes con fechas sin zona/numéricas/offsets inválidos y exportación/reimportación sin duplicar ni degradar revisiones. Dos pruebas de aceptación fallaron antes de la corrección.
2. Dominio API: validación y fórmulas sin requerir red.
3. HTTP: credenciales ausentes → 401; organización distinta → 403; entrada inválida → 400/422.
   `api/tests/test_event_timestamps.py` reproduce nueve casos de coerción de fechas Unix (enteros, decimales y cadenas numéricas en los tres campos temporales). Todos deben devolver 422 y no invocar la ingesta, incluso si el lote contiene primero un evento válido. También verifica texto ISO con UTC/desplazamiento horario y lectura interna de objetos datetime de PostgreSQL.
   `api/tests/test_readiness.py` verifica disponibilidad pública sin caché, separación de liveness, errores de base de datos sin detalles sensibles, recuperación y liberación de conexiones en éxito/error. La prueba de aislamiento llama a `/ready` usando el pool de rol restringido de PostgreSQL.
4. PostgreSQL: inbox idempotente, UPSERT monotónico, aislamiento de consulta y endpoint de indicadores.
5. Entrega: build Vite, build de contenedores y despliegue Pages tras CI en main.

Las pruebas con base se habilitan con RUN_INTEGRATION=1. CI provee PostgreSQL real; sin esa variable quedan omitidas de forma visible. La revisión visual debe comprobar escritorio/móvil, formularios, navegación y recorrido exportar/importar. Las pruebas de carga, penetración, accesibilidad integral y recuperación de backups están pendientes.
