from datetime import datetime, timezone, timedelta
from io import BytesIO
from fastapi.testclient import TestClient
from PIL import Image
from backend.app.main import app

AUTH={}

def login(client):
    response=client.post('/api/admin/login',json={'username':'admin123','password':'admin@123'})
    assert response.status_code==200
    return {'X-CSRF-Token':response.json()['csrf_token']}

def payload():
    return dict(latitude=10.1253,longitude=76.418,contamination_type='Industrial Discharge',description='Dark discharge observed from the riverbank.',observed_at=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat())

def test_full_journey():
    with TestClient(app) as client:
        health = client.get('/api/health').json()
        assert health['datasets_available']
        assert health['map_service'] == 'available'
        assert health['river_engine'] == 'available'
        assert health['persistence_mode'] in ['postgres', 'sqlite-local', 'sqlite-temp']
        for layer in ['river','settlements','intakes','monitoring-points','local-bodies']:
            assert client.get('/api/map/'+layer).json()['features']
        analysis=client.post('/api/analyze',json={'latitude':10.1253,'longitude':76.418})
        assert analysis.status_code==200
        assert analysis.json()['downstream_path']['features']
        img=BytesIO()
        Image.new('RGB',(20,20),'blue').save(img,'PNG')
        upload=client.post('/api/uploads',files={'file':('evidence.png',img.getvalue(),'image/png')})
        assert upload.status_code==201
        data=payload();data['image_url']=upload.json()['image_url'];data['contact']='private@example.com'
        response=client.post('/api/reports',json=data)
        assert response.status_code==201,response.text
        report=response.json(); rid=report['id']
        assert 'contact' not in report
        assert report['status']=='UNVERIFIED'
        assert report['priority_level']=='HIGH'
        assert client.get(data['image_url']).status_code==200
        assert client.get('/api/reports/'+rid+'/impact').json()['status']=='UNVERIFIED'
        alerts=client.get('/api/reports/'+rid+'/alerts').json()
        assert len(alerts)==6
        assert client.patch('/api/reports/'+rid+'/status',json={'status':'VERIFIED'}).status_code==401
        auth=login(client)
        assert len(client.post('/api/reports/'+rid+'/alerts',headers=auth).json())==len(alerts)
        for state in ['UNDER REVIEW','VERIFIED','RESOLVED']:
            assert client.patch('/api/reports/'+rid+'/status',headers=auth,json={'status':state,'note':'Checked on site'}).json()['status']==state
        assert client.patch('/api/reports/'+rid+'/status',headers=auth,json={'status':'REJECTED'}).status_code==409
        for state in ['Sent - Simulated','Acknowledged']:
            assert client.patch('/api/alerts/'+alerts[0]['id'],headers=auth,json={'state':state}).json()['state']==state
        assert len(client.get('/api/reports/'+rid).json()['timeline'])>=9
        repeated=client.post('/api/reports',json=payload()).json()
        assert repeated['priority_score']==10
        assert client.get('/api/hotspots').json()[0]['last_30_days']>=2

def test_invalid_inputs_and_missing_dataset():
    with TestClient(app) as client:
        assert client.post('/api/analyze',json={'latitude':90,'longitude':90}).status_code==422
        assert client.post('/api/analyze',json={'latitude':100,'longitude':90}).status_code==422
        assert client.post('/api/reports',json={}).status_code==422
        bad=payload();bad['observed_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        assert client.post('/api/reports',json=bad).status_code==422
        bad=payload();bad['image_url']='/uploads/../../.env'
        assert client.post('/api/reports',json=bad).status_code==422
        assert client.post('/api/uploads',files={'file':('bad.png',b'not an image','image/png')}).status_code==422
        assert client.get('/api/reports/missing').status_code==404
        assert client.get('/api/reports/missing/alerts').status_code==404
        app.state.river=None
        assert client.get('/api/map/river').status_code==503
        assert client.get('/api/health').json()['status']=='degraded'


def test_health_reports_degraded_map_only_mode(monkeypatch):
    from backend.app import database
    monkeypatch.setattr(database, 'database_status', lambda: 'unavailable')
    monkeypatch.setattr(app.state, 'river', object(), raising=False)
    from backend.app.main import health
    result = health()
    assert result['status'] == 'degraded'
    assert result['map_service'] == 'available'
    assert result['database'] == 'unavailable'
