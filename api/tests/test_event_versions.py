import copy
import pytest
from fastapi.testclient import TestClient
from app.domain import Event
from app.main import create_app
from test_api import EVENTS, SpyRepository, auth


@pytest.mark.parametrize('version', [True, False, '1', None, 2])
@pytest.mark.parametrize('invalid_index', [0, 1])
def test_invalid_versions_reject_the_entire_http_batch(auth, version, invalid_index):
    invalid = copy.deepcopy(EVENTS[0])
    invalid['schema_version'] = version
    batch = [EVENTS[0]]
    batch.insert(invalid_index, invalid)
    repo = SpyRepository()
    response = TestClient(create_app(repo)).post('/v1/events', headers=auth, json=batch)
    assert response.status_code == 422
    assert repo.calls == 0
    assert any(error['loc'] == ['body', invalid_index, 'schema_version']
               for error in response.json()['detail'])


@pytest.mark.parametrize('version', [1, 1.0])
def test_numeric_version_one_remains_accepted(auth, version):
    # JSON Schema const: 1 treats 1 and 1.0 as the same number, not as true.
    payload = copy.deepcopy(EVENTS[0])
    payload['schema_version'] = version
    repo = SpyRepository()
    response = TestClient(create_app(repo)).post('/v1/events', headers=auth, json=[payload])
    assert response.status_code == 200
    assert repo.calls == 1
    event = Event.model_validate(payload)
    assert type(event.schema_version) is int and event.schema_version == 1
