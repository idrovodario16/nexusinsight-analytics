import copy
import hashlib
import json
import os
from uuid import UUID
import pytest
from fastapi.testclient import TestClient
from app.access import IntegrationAccess
from app.main import create_app
from test_api import EVENTS, ORG, KEY

OTHER = '22222222-2222-4222-8222-222222222222'
SECOND = 'b' * 40


def credential(key, org, permissions):
    return dict(key_sha256=hashlib.sha256(key.encode()).hexdigest(), organization_id=org, permissions=permissions)


class Repository:
    def __init__(self):
        self.calls = []

    def ingest(self, events):
        self.calls.append(('write', events[0].organization_id))
        return {'accepted_events': len(events)}

    def rows(self, org, *args):
        self.calls.append(('read', org))
        return []

    def aggregate(self, org, *args):
        self.calls.append(('read', org))
        return {'total': 0}


def test_http_tenant_and_permission_boundaries(monkeypatch):
    monkeypatch.setenv('INTEGRATION_CREDENTIALS', json.dumps([
        credential(KEY, ORG, ['read']), credential(SECOND, OTHER, ['write'])]))
    repo = Repository()
    client = TestClient(create_app(repo))
    headers = {'Authorization': 'Bearer ' + KEY, 'X-Organization-ID': ORG}
    for route in ['/v1/metrics', '/v1/operations']:
        assert client.get(route, headers=headers).status_code == 200
        assert client.get(route, headers={**headers, 'X-Organization-ID': OTHER}).status_code == 403
        assert client.get(route, headers={**headers, 'Authorization': 'Bearer ' + SECOND}).status_code == 403
        assert client.get(route).status_code == 401
    assert client.post('/v1/events', headers=headers, json=EVENTS).status_code == 403
    writer = {'Authorization': 'Bearer ' + SECOND, 'X-Organization-ID': OTHER}
    assert client.post('/v1/events', headers=writer, json=EVENTS).status_code == 403
    assert all(org == UUID(ORG) for _, org in repo.calls)
    payload = copy.deepcopy(EVENTS[:1])
    payload[0]['organization_id'] = payload[0]['data']['organization_id'] = OTHER
    assert client.post('/v1/events', headers=writer, json=payload).status_code == 200
    assert repo.calls[-1] == ('write', UUID(OTHER))


@pytest.mark.parametrize('config', ['', '[]', '{}', 'null', '[{}]'])
def test_invalid_explicit_configuration_fails_closed(config):
    with pytest.raises(RuntimeError):
        IntegrationAccess(dict(INTEGRATION_CREDENTIALS=config, API_KEY=KEY, ORGANIZATION_ID=ORG))


def test_duplicate_key_rejected():
    config = [credential(KEY, ORG, ['read']), credential(KEY, OTHER, ['write'])]
    with pytest.raises(RuntimeError):
        IntegrationAccess(dict(INTEGRATION_CREDENTIALS=json.dumps(config)))


@pytest.mark.skipif(os.environ.get('RUN_INTEGRATION') != '1', reason='PostgreSQL required')
def test_postgres_same_identifiers_are_isolated_by_organization(monkeypatch):
    from uuid import uuid4
    from sqlalchemy import text
    from app.domain import Event
    from app.repository import PostgresRepository
    org_a, org_b = str(uuid4()), str(uuid4())
    payload = copy.deepcopy(EVENTS[0])
    payload['event_id'] = str(uuid4())
    payload['data']['id'] = str(uuid4())
    repo = PostgresRepository(os.environ['DATABASE_URL'])
    monkeypatch.setenv('INTEGRATION_CREDENTIALS', json.dumps([
        credential(KEY, org_a, ['read', 'write']), credential(SECOND, org_b, ['read', 'write'])]))
    client = TestClient(create_app(repo))
    try:
        for key, org, value in [(KEY, org_a, 100), (SECOND, org_b, 900)]:
            payload['organization_id'] = payload['data']['organization_id'] = org
            payload['data']['amount_cents'] = value
            headers = {'Authorization': 'Bearer ' + key, 'X-Organization-ID': org}
            response = client.post('/v1/events', headers=headers, json=[payload])
            assert response.status_code == 200
            assert response.json()['accepted_events'] == 1
            assert client.post('/v1/events', headers=headers, json=[payload]).json()['duplicate_events'] == 1
        for key, org, value in [(KEY, org_a, 100), (SECOND, org_b, 900)]:
            headers = {'Authorization': 'Bearer ' + key, 'X-Organization-ID': org}
            rows = client.get('/v1/operations', headers=headers).json()
            assert len(rows) == 1 and rows[0]['amount_cents'] == value
            assert client.get('/v1/metrics', headers=headers).json()['total'] == 1
    finally:
        with repo.engine.begin() as conn:
            for org in (org_a, org_b):
                conn.execute(text('DELETE FROM inbox WHERE organization_id=:org'), {'org': org})
                conn.execute(text('DELETE FROM operation_facts WHERE organization_id=:org'), {'org': org})
        repo.engine.dispose()
