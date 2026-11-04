import copy
import json
import os
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.domain import Event, metrics
from app.main import create_app

EVENTS = json.loads(Path(__file__).resolve().parents[2].joinpath('examples/operations.events.json').read_text())
ORG = EVENTS[0]['organization_id']
KEY = 'test-only-fictional-key-with-32-characters'

@pytest.fixture
def auth(monkeypatch):
    monkeypatch.setenv('API_KEY', KEY)
    monkeypatch.setenv('ORGANIZATION_ID', ORG)
    return {'Authorization': 'Bearer ' + KEY, 'X-Organization-ID': ORG}

def test_contract_and_metrics():
    rows = [Event.model_validate(e).data for e in EVENTS]
    assert metrics([])['value_cents'] == 0
    assert metrics(rows)['completed'] == 12
    bad = copy.deepcopy(EVENTS[0])
    bad['data']['amount_cents'] = -1
    with pytest.raises(ValidationError):
        Event.model_validate(bad)
    bad = copy.deepcopy(EVENTS[0])
    bad['organization_id'] = str(uuid4())
    with pytest.raises(ValidationError):
        Event.model_validate(bad)

class SpyRepository:
    calls = 0
    def ingest(self, events):
        self.calls += 1
        return {'accepted_events': len(events), 'duplicate_events': 0}

def test_auth_and_atomic_validation(auth):
    repo = SpyRepository()
    client = TestClient(create_app(repo))
    assert client.post('/v1/events', json=EVENTS).status_code == 401
    assert client.post('/v1/events', headers={**auth, 'X-Organization-ID': str(uuid4())}, json=EVENTS).status_code == 403
    bad = copy.deepcopy(EVENTS)
    bad[-1]['data']['amount_cents'] = -1
    assert client.post('/v1/events', headers=auth, json=bad).status_code == 422
    assert repo.calls == 0
    assert client.post('/v1/events', headers=auth, json=EVENTS).status_code == 200
    assert repo.calls == 1

@pytest.mark.skipif(os.environ.get('RUN_INTEGRATION') != '1', reason='PostgreSQL required')
def test_postgres_idempotency_and_revision(auth):
    from app.repository import PostgresRepository
    from sqlalchemy import text
    repo = PostgresRepository(os.environ['DATABASE_URL'])
    payload = copy.deepcopy(EVENTS[0])
    payload['event_id'] = str(uuid4())
    payload['data']['id'] = str(uuid4())
    event = Event.model_validate(payload)
    try:
        assert repo.ingest([event])['accepted_events'] == 1
        assert repo.ingest([event])['duplicate_events'] == 1
        newer = copy.deepcopy(payload)
        newer['event_id'] = str(uuid4())
        newer['data']['revision'] = 3
        newer['data']['status'] = 'completed'
        repo.ingest([Event.model_validate(newer)])
        old = copy.deepcopy(payload)
        old['event_id'] = str(uuid4())
        repo.ingest([Event.model_validate(old)])
        found = [r for r in repo.rows(ORG, limit=1000) if r.id == event.data.id]
        assert len(found) == 1 and found[0].revision == 3
        assert repo.rows(str(uuid4())) == []
        client = TestClient(create_app(repo))
        assert client.get('/v1/metrics', headers=auth).status_code == 200
    finally:
        with repo.engine.begin() as conn:
            conn.execute(text("DELETE FROM inbox WHERE payload->'data'->>'id'=:id"), {'id': str(event.data.id)})
            conn.execute(text('DELETE FROM operation_facts WHERE id=:id'), {'id': str(event.data.id)})
        repo.engine.dispose()
