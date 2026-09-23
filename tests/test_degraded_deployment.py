import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import database
from backend.app.main import app

def test_map_initialization_never_connects_to_database():
    with patch.object(database, 'initialize_database', side_effect=AssertionError('Map tried to open DB')):
        with TestClient(app) as client:
            for layer in ['river','settlements','intakes','monitoring-points','local-bodies']:
                assert client.get('/api/map/'+layer).status_code == 200

def test_database_outage_leaves_analysis_and_map_available(monkeypatch):
    monkeypatch.setattr(database, 'initialize_database', lambda: False)
    with TestClient(app) as client:
        health = client.get('/api/health').json()
        assert health['status'] == 'degraded'
        assert health['map'] == 'available'
        assert health['database'] == 'unavailable'
        result = client.post('/api/analyze', json={'latitude':10.1253,'longitude':76.418})
        assert result.status_code == 200
        assert result.json()['downstream_path']['features']
        assert result.json()['repeat_history_available'] is False
        assert result.json()['warnings']
        for method, path, body in [('get','/api/reports',None), ('post','/api/reports',{}), ('post','/api/admin/login',{'username':'admin123','password':'admin@123'})]:
            response = getattr(client,method)(path, **({'json':body} if body is not None else {}))
            assert response.status_code == 503
            assert response.json()['error'] == 'DATABASE_UNAVAILABLE'

def test_cloud_import_and_requests_without_database_or_blob_from_foreign_cwd(tmp_path):
    root = Path(__file__).resolve().parents[1]
    env = {k:v for k,v in os.environ.items() if k not in ['DATABASE_URL','POSTGRES_URL','POSTGRES_PRISMA_URL','NEON_DATABASE_URL','BLOB_READ_WRITE_TOKEN','BLOB_TOKEN','DATA_DIR','STORAGE_BACKEND']}
    env.update(VERCEL='1', PYTHONPATH=str(root), PYTHON_DOTENV_DISABLED='1')
    script = '''
from api.server import app
from fastapi.testclient import TestClient
from backend.app import database
assert database.engine is None
with TestClient(app) as client:
    assert client.get('/api/health').json()['map'] == 'available'
    assert len(client.get('/api/map/river').json()['features']) == 62
    result = client.post('/api/analyze', json={'latitude':10.1200287,'longitude':76.379479})
    assert result.status_code == 200, result.text
    assert result.json()['repeat_history_available'] is False
    assert client.post('/api/admin/login', json={'username':'admin123','password':'admin@123'}).status_code == 503
print('Cloud entrypoint works without database/blob; real map data included.')
'''
    result = subprocess.run([sys.executable, '-c', script], env=env, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
