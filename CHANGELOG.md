# Cambios

## 2026-11-20 · Fechas de eventos según el contrato v1

- Se rechazan fechas Unix numéricas o cadenas numéricas en `occurred_at`, `created_at` y `updated_at`, antes de invocar al repositorio. El lote completo devuelve 422.
- Se conservan las fechas ISO 8601 con zona horaria y los objetos datetime usados al leer PostgreSQL. La validación se ajusta al contrato v1 ya documentado; no requiere migración de esquema ni modifica registros existentes.
- Regresiones HTTP reproducidas antes de la corrección, pruebas de compatibilidad interna y hoja de ruta revisada con estados y criterios verificables.

## 2026-11-17 · Fase 2

- RLS en tablas empresariales, contexto transaccional y roles de ejecución mínimos.
- Comprobación opcional al arranque para rechazar roles privilegiados o esquemas sin protección.
- Pruebas con rol restringido y conexiones reutilizadas; despliegue separado de migraciones.

## 2026-11-17 · Fase 1

- Autorización de integración extraída a un módulo con credenciales SHA-256 por empresa.
- Permisos read/write, rechazo de configuración ambigua y compatibilidad con API_KEY.
- Pruebas de aislamiento, permisos y configuración; instrucciones para Docker y relay.
- Inbox con deduplicación por empresa y migraciones registradas transaccionalmente.
