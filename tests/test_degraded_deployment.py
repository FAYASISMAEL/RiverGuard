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
            assert response.json()['error'] == 'PERSISTENCE_UNAVAILABLE'
