import copy
import json
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from fastapi.testclient import TestClient
from app.database_security import verify_database_isolation
from app.domain import Event
from app.main import create_app
from app.repository import PostgresRepository
from test_api import EVENTS, KEY
from test_access import credential, SECOND


def test_empty_and_mixed_batches_do_not_open_a_transaction():
    repo = object.__new__(PostgresRepository)
    assert repo.ingest([]) == {'accepted_events': 0, 'duplicate_events': 0}
    first = Event.model_validate(EVENTS[0])
    other = copy.deepcopy(EVENTS[0])
    other['organization_id'] = other['data']['organization_id'] = str(uuid4())
    with pytest.raises(ValueError, match='one organization'):
        repo.ingest([first, Event.model_validate(other)])


@pytest.mark.skipif(os.environ.get('RUN_INTEGRATION') != '1', reason='PostgreSQL required')
def test_rls_unfiltered_queries_writes_http_and_pool_cleanup(monkeypatch):
    admin = create_engine(os.environ['DATABASE_URL'])
    url = make_url(os.environ['DATABASE_URL']).update_query_dict({'options': '-c role=nexus_insight_runtime'})
    repo = PostgresRepository(url)
    # A single physical connection forces reuse after commits and rollbacks.
    repo.engine.dispose()
    repo.engine = create_engine(url, pool_size=1, max_overflow=0)
    org_a, org_b = str(uuid4()), str(uuid4())
    monkeypatch.setenv('INTEGRATION_CREDENTIALS', json.dumps([
        credential(KEY, org_a, ['read', 'write']), credential(SECOND, org_b, ['read', 'write'])]))
    client = TestClient(create_app(repo))
    payload = copy.deepcopy(EVENTS[0])
    payload['event_id'] = str(uuid4())
    payload['data']['id'] = str(uuid4())
    try:
        with pytest.raises(RuntimeError, match='non-owner'):
            verify_database_isolation(admin)
        verify_database_isolation(repo.engine)
        readiness = client.get('/ready')
        assert readiness.status_code == 200 and readiness.json()['status'] == 'ready'
        assert readiness.headers['cache-control'] == 'no-store'
        monkeypatch.setenv('REQUIRE_DATABASE_ISOLATION', '1')
        with pytest.raises(RuntimeError, match='non-owner'):
            PostgresRepository(os.environ['DATABASE_URL'])
        for key, org, amount in [(KEY, org_a, 100), (SECOND, org_b, 900)]:
            headers = {'Authorization': 'Bearer ' + key, 'X-Organization-ID': org}
            payload['organization_id'] = payload['data']['organization_id'] = org
            payload['data']['amount_cents'] = amount
            response = client.post('/v1/events', headers=headers, json=[payload])
            assert response.status_code == 200 and response.json()['accepted_events'] == 1
            assert client.post('/v1/events', headers=headers, json=[payload]).json()['duplicate_events'] == 1
            rows = client.get('/v1/operations', headers=headers).json()
            assert len(rows) == 1 and rows[0]['amount_cents'] == amount
            assert client.get('/v1/metrics', headers=headers).json()['total'] == 1
        with repo.engine.connect() as conn:
            for table in ('inbox', 'operation_facts'):
                assert conn.execute(text('SELECT * FROM ' + table)).all() == []
        with repo.tenant(org_a) as conn:
            assert [str(r[0]) for r in conn.execute(text('SELECT organization_id FROM operation_facts'))] == [org_a]
            assert conn.execute(text('UPDATE operation_facts SET amount_cents=0 WHERE organization_id=:b'), {'b': org_b}).rowcount == 0
        with pytest.raises(DBAPIError) as denied:
            with repo.tenant(org_a) as conn:
                conn.execute(text('UPDATE operation_facts SET organization_id=:b'), {'b': org_b})
        assert denied.value.orig.sqlstate == '42501'
        with pytest.raises(DBAPIError) as denied:
            with repo.tenant(org_a) as conn:
                conn.execute(text("INSERT INTO inbox(organization_id,event_id,payload) VALUES(:b,:id,'{}')"),
                             {'b': org_b, 'id': str(uuid4())})
        assert denied.value.orig.sqlstate == '42501'
        with repo.engine.connect() as conn:
            assert conn.execute(text('SELECT * FROM operation_facts')).all() == []
        assert repo.rows(org_b)[0].amount_cents == 900
        with pytest.raises(DBAPIError) as denied:
            with repo.engine.begin() as conn:
                conn.execute(text('TRUNCATE inbox'))
        assert denied.value.orig.sqlstate == '42501'
    finally:
        with admin.begin() as conn:
            for org in (org_a, org_b):
                conn.execute(text('DELETE FROM inbox WHERE organization_id=:org'), {'org': org})
                conn.execute(text('DELETE FROM operation_facts WHERE organization_id=:org'), {'org': org})
        repo.engine.dispose()
        admin.dispose()
