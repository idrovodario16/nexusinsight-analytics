# Arquitectura de NexusInsight

## C4: contexto
El usuario explora una demo React independiente. Un integrador usa la API autenticada del producto. Insight recibe instantáneas de Core o de cualquier productor compatible y prepara un modelo de consulta propio. Ningún producto consulta la base del otro.

## C4: contenedores
React/Vite estático; API FastAPI/Python; PostgreSQL exclusivo; relay HTTP externo y opcional. La demo y la API no están conectadas entre sí en esta versión. El despliegue local incluye web, API y DB. Pages aloja únicamente React.

## C4: componentes
HTTP valida credenciales y contrato; repositorio ingiere inbox y actualiza facts en una transacción; consulta SQL filtra por organización; dominio mantiene el contrato y las fórmulas.

## Modelo de datos
`inbox(event_id PK, organization_id, payload JSONB, received_at)` deduplica transporte. `operation_facts(organization_id, id PK compuesto, title, sector, status, amount_cents, revision, created_at, updated_at)` contiene la última revisión, no una fila por evento. El UPSERT usa `WHERE current.revision < excluded.revision`. Los indicadores agregan facts, nunca eventos.

Los índices compuestos empiezan por organization_id. La credencial de esta instancia solo da acceso al tenant configurado. No se declara aislamiento multiusuario de producción. Fechas de creación inmutables; estados terminales en Core; revisiones monotónicas en Insight. El esquema SQL inicial es idempotente. Para cambios posteriores se deben añadir migraciones numeradas; no editar retrospectivamente el SQL aplicado en entornos persistentes.

## Consistencia y límites
Integración eventual y entrega al menos una vez. El relay confirma checkpoint solo al terminar la ingestión. El evento es un snapshot completo: se puede reconstruir facts desde outbox. Borrados, cambios de moneda, conflictos de mismo ID/revisión con datos distintos y cambio de organización quedan fuera del contrato v1. Solo el productor dueño del registro puede emitir revisiones válidas. Se conservan inbox/outbox sin política automática de limpieza; la retención debe definirse antes de operar a escala.

El desglose C4 y las decisiones compartidas están en [nexus-architecture](https://github.com/idrovodario16/nexus-architecture).
