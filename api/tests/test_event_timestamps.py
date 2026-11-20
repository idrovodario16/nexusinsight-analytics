import copy
from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from app.domain import Event
from app.main import create_app
from test_api import EVENTS, SpyRepository, auth


def set_timestamp(event, field, value):
    target = event if field == 'occurred_at' else event['data']
    target[field] = value


@pytest.mark.parametrize('field', ['occurred_at', 'created_at', 'updated_at'])
@pytest.mark.parametrize('value', [1704067200, 1704067200.5, '1704067200'])
def test_epoch_timestamps_reject_the_entire_http_batch(auth, field, value):
    repo = SpyRepository()
    client = TestClient(create_app(repo))
    invalid = copy.deepcopy(EVENTS[0])
    set_timestamp(invalid, field, value)
    response = client.post('/v1/events', headers=auth, json=[EVENTS[0], invalid])
    assert response.status_code == 422
    assert repo.calls == 0
    assert any(error['loc'][-1] == field for error in response.json()['detail'])


@pytest.mark.parametrize('timestamp', ['2026-11-20T09:00:00Z', '2026-11-20T09:00:00.123-05:00'])
def test_iso_timestamps_with_timezone_remain_accepted(auth, timestamp):
    payload = copy.deepcopy(EVENTS[0])
    for field in ('occurred_at', 'created_at', 'updated_at'):
        set_timestamp(payload, field, timestamp)
    repo = SpyRepository()
    response = TestClient(create_app(repo)).post('/v1/events', headers=auth, json=[payload])
    assert response.status_code == 200
    assert repo.calls == 1
    parsed = Event.model_validate(payload)
    expected = datetime.fromisoformat(timestamp)
    assert parsed.occurred_at == parsed.data.created_at == parsed.data.updated_at == expected


@pytest.mark.parametrize('field', ['occurred_at', 'created_at', 'updated_at'])
def test_timezone_is_still_required(auth, field):
    payload = copy.deepcopy(EVENTS[0])
    set_timestamp(payload, field, '2026-11-20T09:00:00')
    repo = SpyRepository()
    response = TestClient(create_app(repo)).post('/v1/events', headers=auth, json=[payload])
    assert response.status_code == 422
    assert repo.calls == 0


def test_internal_datetime_objects_remain_supported():
    event = Event.model_validate(EVENTS[0])
    # SQLAlchemy returns datetime objects when reading operation_facts.
    assert Event.model_validate(event.model_dump()) == event
