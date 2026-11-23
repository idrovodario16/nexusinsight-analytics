from sqlalchemy import create_engine, text
from contextlib import contextmanager
from uuid import UUID
import os
from app.database_security import verify_database_isolation
from app.domain import Event, Operation

class PostgresRepository:
    def __init__(self, url):
        self.engine = create_engine(url, pool_pre_ping=True)
        if os.environ.get('REQUIRE_DATABASE_ISOLATION') == '1':
            try:
                verify_database_isolation(self.engine)
            except Exception:
                self.engine.dispose()
                raise

    def ping(self):
        with self.engine.connect() as conn:
            conn.execute(text('SELECT 1'))

    @contextmanager
    def tenant(self, org):
        org = str(UUID(str(org)))
        with self.engine.begin() as conn:
            conn.execute(text("SELECT set_config('nexus.organization_id', :org, true)"), {'org': org})
            yield conn

    def ingest(self, events):
        if not events:
            return {'accepted_events': 0, 'duplicate_events': 0}
        tenants = {e.organization_id for e in events}
        if len(tenants) != 1:
            raise ValueError('A batch must belong to one organization')
        org = str(next(iter(tenants)))
        accepted = 0
        with self.tenant(org) as conn:
            conn.execute(text('SELECT pg_advisory_xact_lock(hashtext(:org))'), {'org': org})
            for event in events:
                payload = event.model_dump_json()
                inserted = conn.execute(text('''INSERT INTO inbox(event_id,organization_id,payload)
                    VALUES(:id,:org,CAST(:payload AS jsonb)) ON CONFLICT(organization_id,event_id) DO NOTHING RETURNING event_id'''),
                    {'id': str(event.event_id), 'org': str(event.organization_id), 'payload': payload}).first()
                if not inserted:
                    continue
                row = event.data
                values = row.model_dump(mode='json')
                conn.execute(text('''INSERT INTO operation_facts
                    (id,organization_id,title,sector,status,amount_cents,revision,created_at,updated_at)
                    VALUES(:id,:organization_id,:title,:sector,:status,:amount_cents,:revision,:created_at,:updated_at)
                    ON CONFLICT(organization_id,id) DO UPDATE SET title=EXCLUDED.title,sector=EXCLUDED.sector,
                    status=EXCLUDED.status,amount_cents=EXCLUDED.amount_cents,revision=EXCLUDED.revision,
                    updated_at=EXCLUDED.updated_at WHERE operation_facts.revision < EXCLUDED.revision'''), values)
                accepted += 1
        return {'accepted_events': accepted, 'duplicate_events': len(events) - accepted}

    def rows(self, org, sector=None, status=None, offset=0, limit=100):
        query = 'SELECT * FROM operation_facts WHERE organization_id=:org'
        params = {'org': str(org), 'offset': offset, 'limit': limit}
        if sector:
            query += ' AND sector=:sector'
            params['sector'] = sector
        if status:
            query += ' AND status=:status'
            params['status'] = status
        query += ' ORDER BY created_at DESC,id LIMIT :limit OFFSET :offset'
        with self.tenant(org) as conn:
            return [Operation.model_validate(dict(r)) for r in conn.execute(text(query), params).mappings()]

    def aggregate(self, org, sector=None, status=None):
        query = '''SELECT COUNT(*) AS total,
            COUNT(*) FILTER(WHERE status='completed') AS completed,
            COUNT(*) FILTER(WHERE status IN ('pending','in_progress')) AS open,
            COALESCE(SUM(amount_cents) FILTER(WHERE status='completed'),0) AS value_cents
            FROM operation_facts WHERE organization_id=:org'''
        params = {'org': str(org)}
        if sector:
            query += ' AND sector=:sector'
            params['sector'] = sector
        if status:
            query += ' AND status=:status'
            params['status'] = status
        with self.tenant(org) as conn:
            row = dict(conn.execute(text(query), params).mappings().one())
        row = {k: int(v) for k, v in row.items()}
        row['completion'] = round(row['completed'] / row['total'] * 100, 2) if row['total'] else 0
        return row
