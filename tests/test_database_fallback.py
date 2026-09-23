"""Exercise real login/report persistence while the preferred database fails."""
import os
import subprocess
import sys
from pathlib import Path
import pytest

@pytest.mark.parametrize('scenario', ['missing', 'invalid', 'timeout', 'auth', 'unreachable', 'local'])
def test_fallback_admin_and_reports(tmp_path, scenario):
    root = Path(__file__).resolve().parents[1]
    excluded = ['DATABASE_URL','POSTGRES_URL','POSTGRES_PRISMA_URL','NEON_DATABASE_URL','BLOB_READ_WRITE_TOKEN','BLOB_TOKEN','DATA_DIR','STORAGE_BACKEND','VERCEL']
    env = {k:v for k,v in os.environ.items() if k not in excluded}
    env.update(PYTHONPATH=str(root), PYTHON_DOTENV_DISABLED='1', SCENARIO=scenario)
    if scenario != 'local':
        env['VERCEL'] = '1'
    if scenario == 'invalid':
        env['DATABASE_URL'] = 'invalid connection URL'
    elif scenario in ['timeout','auth','unreachable']:
        env['DATABASE_URL'] = 'postgresql://test:test@127.0.0.1:1/test'
    script = r'''
import os
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone
from backend.app import config
# Isolate the actual SQLite database under the test directory on every OS.
config.FALLBACK_DATABASE_PATH = Path.cwd() / 'nested' / 'fallback.db'
scenario = os.environ['SCENARIO']
import psycopg
failure = psycopg.OperationalError('timeout' if scenario == 'timeout' else 'authentication failed')
with patch('psycopg.connect', side_effect=failure) if scenario in ['timeout','auth'] else __import__('contextlib').nullcontext():
    from api.server import app
    from backend.app import database
    from fastapi.testclient import TestClient
    with TestClient(app, base_url='https://testserver') as client:
        health = client.get('/api/health').json()
        assert health['database'] == ('sqlite-local' if scenario == 'local' else 'sqlite-temp'), health
        assert health['admin'] == health['reports'] == 'available'
        assert len(client.get('/api/map/river').json()['features']) == 62
        response = client.post('/api/admin/login', json={'username':'admin123','password':'admin@123'})
        assert response.status_code == 200, response.text
        assert 'HttpOnly' in response.headers['set-cookie']
        if scenario != 'local': assert 'Secure' in response.headers['set-cookie']
        auth = {'X-CSRF-Token': response.json()['csrf_token']}
        assert client.get('/api/admin/session').status_code == 200
        data = dict(latitude=10.1200287,longitude=76.379479,contamination_type='Industrial Discharge',description='SAMPLE fallback database test report',observed_at=datetime.now(timezone.utc).isoformat())
        for states in [['UNDER REVIEW','VERIFIED','RESOLVED'], ['REJECTED']]:
            created = client.post('/api/reports', json=data)
            assert created.status_code == 201, created.text
            rid = created.json()['id']
            for state in states:
                changed = client.patch('/api/reports/'+rid+'/status', headers=auth, json={'status':state,'note':'Fallback verification'})
                assert changed.status_code == 200, changed.text
                assert changed.json()['status'] == state
            detail = client.get('/api/reports/'+rid).json()
            assert detail['timeline']
        assert len(client.get('/api/reports').json()) == 2
        assert client.get('/api/admin/reports').status_code == 200
        selected = database.engine
        assert database.get_database_engine() is selected
        assert client.get('/api/admin/session').status_code == 200
        assert client.post('/api/analyze', json={'latitude':data['latitude'],'longitude':data['longitude']}).status_code == 200
    # Reopening a warm instance's file must preserve existing reports/tables.
    database._ready = False
    with TestClient(app, base_url='https://testserver') as client:
        assert len(client.get('/api/reports').json()) == 2
print('Fallback login, reports, status transitions, history, map and analysis passed.')
'''
    result = subprocess.run([sys.executable, '-c', script], env=env, cwd=tmp_path, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr


def test_preferred_postgres_is_kept_and_fails_over_after_outage(monkeypatch, tmp_path):
    from unittest.mock import MagicMock
    from backend.app import database, config
    preferred = MagicMock()
    preferred.dialect.name = 'postgresql'
    monkeypatch.setattr(database, 'engine', preferred)
    monkeypatch.setattr(database, '_ready', False)
    monkeypatch.setattr(database, '_retry_after', 0)
    monkeypatch.setattr(database, 'SessionLocal', database.sessionmaker(expire_on_commit=False))
    monkeypatch.setattr(config, 'FALLBACK_DATABASE_PATH', tmp_path/'fallback.db')
    assert database.get_database_engine() is preferred
    preferred.begin.assert_called_once()
    preferred.connect.side_effect = ConnectionError('connection lost')
    active = database.get_database_engine()
    assert active is not None
    assert active.dialect.name == 'sqlite'
    assert database.get_database_engine() is active
    active.dispose()


def test_all_options_fail_returns_controlled_error(monkeypatch):
    from backend.app import database
    from backend.app.main import app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(database, 'engine', None)
    monkeypatch.setattr(database, '_ready', False)
    monkeypatch.setattr(database, '_retry_after', 0)
    monkeypatch.setattr(database, 'make_engine', lambda url: None)
    with TestClient(app) as client:
        response = client.post('/api/admin/login', json={'username':'admin123','password':'admin@123'})
        assert response.status_code == 503
        assert response.json()['error'] == 'PERSISTENCE_UNAVAILABLE'
        assert client.get('/api/map/river').status_code == 200
