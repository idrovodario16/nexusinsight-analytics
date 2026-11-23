from contextlib import contextmanager
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from app.main import create_app
from app.repository import PostgresRepository

KEY = 'readiness-fictional-key-at-least-32-characters'
ORG = '11111111-1111-4111-8111-111111111111'

class ReadinessRepository:
    def __init__(self):
        self.calls = 0
        self.failure = None

    def ping(self):
        self.calls += 1
        if self.failure:
            raise self.failure

def client_for(repo, monkeypatch):
    monkeypatch.delenv('INTEGRATION_CREDENTIALS', raising=False)
    monkeypatch.setenv('API_KEY', KEY)
    monkeypatch.setenv('ORGANIZATION_ID', ORG)
    return TestClient(create_app(repo))

def test_readiness_success_is_public_uncached_and_checks_each_request(monkeypatch):
    repo = ReadinessRepository()
    client = client_for(repo, monkeypatch)
    assert client.get('/health').status_code == 200
    assert repo.calls == 0
    for expected in (1, 2):
        response = client.get('/ready')
        assert response.status_code == 200
        assert response.json() == {'status': 'ready', 'service': 'nexusinsight', 'version': '0.1.0'}
        assert response.headers['cache-control'] == 'no-store'
        assert repo.calls == expected

def test_database_failure_is_sanitized_and_recovers_without_affecting_liveness(monkeypatch):
    repo = ReadinessRepository()
    repo.failure = OperationalError('SELECT 1', {}, Exception('fictional-secret-in-error'))
    client = client_for(repo, monkeypatch)
    response = client.get('/ready')
    assert response.status_code == 503
    assert response.json() == {'detail': 'Database unavailable'}
    assert response.headers['cache-control'] == 'no-store'
    assert 'fictional-secret' not in response.text
    assert client.get('/health').status_code == 200
    assert repo.calls == 1
    repo.failure = None
    assert client.get('/ready').status_code == 200
    assert repo.calls == 2

def test_ping_uses_only_select_one_and_releases_connection_on_success_or_failure():
    for fail in (False, True):
        statements = []
        released = []

        class Connection:
            def execute(self, statement):
                statements.append(str(statement))
                if fail:
                    raise OperationalError('SELECT 1', {}, Exception('fictional connection failure'))

        class Engine:
            @contextmanager
            def connect(self):
                try:
                    yield Connection()
                finally:
                    released.append(True)

        repo = object.__new__(PostgresRepository)
        repo.engine = Engine()
        if fail:
            with pytest.raises(OperationalError):
                repo.ping()
        else:
            repo.ping()
        assert statements == ['SELECT 1']
        assert released == [True]
