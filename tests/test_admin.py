from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import AdminSession, now
from sqlalchemy import select
from datetime import timedelta
import pytest

@pytest.mark.parametrize('host', ['localhost', '127.0.0.1'])
def test_proxy_preserves_same_origin_on_alternate_vite_port(host):
    origin = f'http://{host}:5175'
    with TestClient(app, base_url=origin) as client:
        result = client.post('/api/admin/login', headers={'Origin':origin}, json={'username':'admin123','password':'admin@123'})
        assert result.status_code == 200, result.text
        csrf = result.json()['csrf_token']
        rid = client.post('/api/demo').json()['id']
        path = f'/api/admin/reports/{rid}/opened'
        assert client.post(path, headers={'Origin':origin,'X-CSRF-Token':csrf}).status_code == 200
        assert client.post(path, headers={'Origin':origin}).status_code == 403
        assert client.post(path, headers={'Origin':'https://untrusted.example','X-CSRF-Token':csrf}).status_code == 403

@pytest.mark.parametrize('origin', ['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost:5174', 'http://127.0.0.1:5174'])
def test_local_frontend_origins_support_login_session_and_logout(origin):
    with TestClient(app) as client:
        preflight=client.options('/api/admin/login', headers={'Origin':origin, 'Access-Control-Request-Method':'POST', 'Access-Control-Request-Headers':'content-type'})
        assert preflight.status_code==200
        assert preflight.headers['access-control-allow-origin']==origin
        result=client.post('/api/admin/login',headers={'Origin':origin},json={'username':'admin123','password':'admin@123'})
        assert result.status_code==200, result.text
        assert client.get('/api/admin/session').status_code==200
        csrf=result.json()['csrf_token']
        assert client.post('/api/admin/logout',headers={'Origin':'https://untrusted.example','X-CSRF-Token':csrf}).status_code==403
        assert client.post('/api/admin/logout',headers={'Origin':origin,'X-CSRF-Token':csrf}).status_code==200

def test_admin_auth_case_persistence_and_append_only_history():
    with TestClient(app) as client:
        for url in ['/api/admin/session','/api/admin/dashboard','/api/admin/reports','/api/admin/cases']:
            assert client.get(url).status_code==401
        assert client.post('/api/admin/login',json={'username':'Admin123','password':'admin@123'}).status_code==401
        result=client.post('/api/admin/login',json={'username':'admin123','password':'admin@123'})
        assert result.status_code==200
        assert 'HttpOnly' in result.headers['set-cookie']
        auth={'X-CSRF-Token':result.json()['csrf_token']}
        report=client.post('/api/demo').json();rid=report['id'];original=report['timeline']
        assert client.patch(f'/api/reports/{rid}/status',json={'status':'VERIFIED'}).status_code==403
        assert client.post(f'/api/admin/reports/{rid}/opened',headers=auth).status_code==200
        case_id=None
        for status in ['UNDER REVIEW','VERIFIED','RESOLVED']:
            result=client.patch(f'/api/reports/{rid}/status',headers=auth,json={'status':status}).json()
            assert result['timeline'][:len(original)]==original
            assert result['case']['original_report_id']==rid
            if case_id: assert result['case']['id']==case_id
            case_id=result['case']['id']
        assert case_id.startswith('CASE-')
        assert any(r['id']==rid for r in client.get('/api/admin/cases').json())
        assert client.get('/api/admin/dashboard').json()['statuses']['RESOLVED']>=1
        assert client.post('/api/admin/logout',headers=auth).status_code==200
        assert client.get('/api/admin/session').status_code==401
        public=client.get(f'/api/reports/{rid}').json()
        assert public['status']=='RESOLVED' and public['case']['id']==case_id
    # New app lifespan/database session: no history or case data disappeared.
    with TestClient(app) as client:
        assert client.get(f'/api/reports/{rid}').json()['case']['id']==case_id

def test_expired_session_and_cross_origin_login_are_rejected():
    with TestClient(app) as client:
        assert client.post('/api/admin/login',headers={'Origin':'https://untrusted.example'},json={'username':'admin123','password':'admin@123'}).status_code==403
        assert client.post('/api/admin/login',json={'username':'admin123','password':'admin@123'}).status_code==200
        with SessionLocal() as db:
            for session in db.scalars(select(AdminSession)).all():session.expires_at=now()-timedelta(seconds=1)
            db.commit()
        assert client.get('/api/admin/session').status_code==401
