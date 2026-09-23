from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
from backend.app import config
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import UploadedAsset
from datetime import datetime, timezone


def payload():
    return {'latitude':10.1253, 'longitude':76.418, 'contamination_type':'Dead Fish',
            'description':'Three photos of a sample river observation.',
            'observed_at':datetime.now(timezone.utc).isoformat()}


def photo():
    output = BytesIO()
    Image.new('RGB', (30, 30), 'yellow').save(output, 'PNG')
    return output.getvalue()


def test_blob_evidence_persists_without_local_files(monkeypatch, tmp_path):
    monkeypatch.setattr(config, 'STORAGE_BACKEND', 'vercel_blob')
    monkeypatch.setattr(config, 'BLOB_READ_WRITE_TOKEN', 'test-token')
    monkeypatch.setattr(config, 'UPLOAD_DIR', tmp_path / 'must-not-be-created')
    with patch('vercel.blob.BlobClient', autospec=True) as client_type:
        blob = client_type.return_value.__enter__.return_value
        blob.put.side_effect = lambda name, content, **kwargs: SimpleNamespace(url='https://test.public.blob.vercel-storage.com/' + name)
        with TestClient(app) as client:
            urls = []
            for _ in range(3):
                result = client.post('/api/uploads', files={'file': ('photo.png', photo(), 'image/png')})
                assert result.status_code == 201, result.text
                urls.append(result.json()['image_url'])
            assert blob.put.call_count == 3
            saved_bytes = blob.put.call_args.args[1]
            assert Image.open(BytesIO(saved_bytes)).format == 'JPEG'
            assert blob.put.call_args.kwargs['access'] == 'public'
            body = {**payload(), 'image_urls': urls}
            result = client.post('/api/reports', json=body)
            assert result.status_code == 201, result.text
            report_id = result.json()['id']
            assert not config.UPLOAD_DIR.exists()
        # A new app lifespan can resolve photos using DB records, without local files.
        with TestClient(app) as client:
            assert client.get('/api/reports/' + report_id).json()['image_urls'] == urls
            for url in urls:
                response = client.get(url, follow_redirects=False)
                assert response.status_code == 307
                assert response.headers['location'].startswith('https://test.public.blob.vercel-storage.com/evidence/')
            forged = {**payload(), 'image_urls': ['/uploads/' + 'f'*32 + '.jpg']}
            assert client.post('/api/reports', json=forged).status_code == 422
            assert client.get(forged['image_urls'][0]).status_code == 404


def test_blob_failure_is_readable_and_does_not_register_upload(monkeypatch):
    monkeypatch.setattr(config, 'STORAGE_BACKEND', 'vercel_blob')
    monkeypatch.setattr(config, 'BLOB_READ_WRITE_TOKEN', '')
    with TestClient(app) as client:
        response = client.post('/api/uploads', files={'file': ('photo.png', photo(), 'image/png')})
        assert response.status_code == 503
        assert response.json()['detail'] == 'We could not store this photo right now. Please try again.'
        with SessionLocal() as db:
            assert db.query(UploadedAsset).count() == 0


def test_deployment_upload_limit_is_exposed_and_enforced(monkeypatch):
    monkeypatch.setattr(config, 'MAX_IMAGE_BYTES', 4*1024*1024)
    with TestClient(app) as client:
        assert client.get('/api/config').json()['max_image_bytes'] == 4*1024*1024
        response = client.post('/api/uploads', files={'file': ('large.png', b'x'*(4*1024*1024+1), 'image/png')})
        assert response.status_code == 413
        assert '4 MB' in response.json()['detail']


def test_serverless_initializes_without_lifespan_events(monkeypatch):
    monkeypatch.setattr(config, 'IS_VERCEL', True)
    monkeypatch.setattr(app.state, 'initialized', False, raising=False)
    # No context manager: TestClient does not send startup/lifespan messages.
    client = TestClient(app)
    try:
        response = client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['datasets_available']
        assert client.get('/api/map/river').json()['features']
        assert client.post('/api/admin/login', json={'username':'admin123', 'password':'admin@123'}).status_code == 200
    finally:
        client.close()
