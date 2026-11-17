import os
from pathlib import Path
import psycopg
with psycopg.connect(os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')) as connection:
    connection.execute("SELECT pg_advisory_xact_lock(hashtext('nexusinsight_migrations'))")
    connection.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())')
    for migration in sorted(Path(__file__).with_name('db').glob('*.sql')):
        if connection.execute('SELECT 1 FROM schema_migrations WHERE name=%s', (migration.name,)).fetchone():
            continue
        # 001 is idempotent, including on installations predating this ledger.
        connection.execute(migration.read_text())
        connection.execute('INSERT INTO schema_migrations(name) VALUES(%s)', (migration.name,))
print('Schema ready')
