# Cambios

## 2026-11-23 · Disponibilidad de PostgreSQL

- Nueva ruta pública GET /ready: consulta SELECT 1 con el pool existente y devuelve 200 si la base responde o 503 con mensaje genérico ante un error de base de datos.
- Respuestas sin caché, sin consultas a datos empresariales y con liberación de la conexión. /health conserva la señal de vida del proceso.
- Pruebas de fallo/recuperación, sanitización de errores, liberación de conexiones y PostgreSQL con rol restringido. OpenAPI, README y hoja de ruta actualizados; alertas, métricas del relay y recuperación de respaldos siguen pendientes.

## 2026-11-20 · Fechas de eventos según el contrato v1

- Se rechazan fechas Unix numéricas o cadenas numéricas en `occurred_at`, `created_at` y `updated_at`, antes de invocar al repositorio. El lote completo devuelve 422.
- Se conservan las fechas ISO 8601 con zona horaria y los objetos datetime usados al leer PostgreSQL. La validación se ajusta al contrato v1 ya documentado; no requiere migración de esquema ni modifica registros existentes.
- Regresiones HTTP reproducidas antes de la corrección, pruebas de compatibilidad interna y hoja de ruta revisada con estados y criterios verificables.

## 2026-11-19 · Revalidación de dependencias

- GitHub retiró el aviso GHSA-fc5q-39xc-vjpf el 18/11: https://github.com/advisories/GHSA-fc5q-39xc-vjpf.
- npm audit web devuelve cero alertas en ambos productos en la revisión del 19/11. No se cambiaron paquetes ni locks por este aviso. El resultado no certifica la seguridad general del sistema.

## 2026-11-18 · Identidad de operaciones importadas

- La importación JSON normaliza los UUID antes de comparar empresas y fusionar revisiones. El mismo identificador en mayúsculas/minúsculas ya no duplica operaciones ni indicadores.
- En cada importación se reconcilian también las filas existentes, conservando la revisión mayor y sin modificar los datos de entrada. Un lote inválido sigue rechazándose completo.
- Regresiones reproducidas antes de corregir y hoja de ruta actualizada. Pendiente: alerta de seguridad en dependencias de desarrollo detectada por npm audit.

## 2026-11-17 · Fase 2

- RLS en tablas empresariales, contexto transaccional y roles de ejecución mínimos.
- Comprobación opcional al arranque para rechazar roles privilegiados o esquemas sin protección.
- Pruebas con rol restringido y conexiones reutilizadas; despliegue separado de migraciones.

## 2026-11-17 · Fase 1

- Autorización de integración extraída a un módulo con credenciales SHA-256 por empresa.
- Permisos read/write, rechazo de configuración ambigua y compatibilidad con API_KEY.
- Pruebas de aislamiento, permisos y configuración; instrucciones para Docker y relay.
- Inbox con deduplicación por empresa y migraciones registradas transaccionalmente.
