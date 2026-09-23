from io import BytesIO
from datetime import timedelta
from PIL import Image
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models import now
from backend.app.config import MAX_IMAGES_PER_REPORT

def test_multiple_images_gallery_references_and_emergency_actions():
    with TestClient(app) as client:
        urls=[]
        for color in ['yellow','orange','brown']:
            output=BytesIO();Image.new('RGB',(50,50),color).save(output,'PNG')
            r=client.post('/api/uploads',files={'file':('evidence.png',output.getvalue(),'image/png')})
            assert r.status_code==201
            urls.append(r.json()['image_url'])
        body={'latitude':10.1253,'longitude':76.418,'contamination_type':'Dead Fish','description':'Test observation with three evidence photos.','observed_at':(now()-timedelta(minutes=2)).isoformat(),'image_urls':urls}
        r=client.post('/api/reports',json=body)
        assert r.status_code==201,r.text
        report=r.json();rid=report['id']
        assert report['image_urls']==urls and report['image_url']==urls[0]
        assert any(e['label']=='Evidence images uploaded' for e in report['timeline'])
        assert all(client.get(url).status_code==200 for url in urls)
        auth={'X-CSRF-Token':client.post('/api/admin/login',json={'username':'admin123','password':'admin@123'}).json()['csrf_token']}
        assert client.post(f'/api/admin/reports/{rid}/actions',json={'action':'Mark Under Control'},headers=auth).status_code==409
        for state in ['UNDER REVIEW','VERIFIED']:
            assert client.patch(f'/api/reports/{rid}/status',json={'status':state},headers=auth).status_code==200
        original=client.get(f'/api/reports/{rid}').json()['timeline']
        for action in ['Generate Authority Alert','Notify Water Intake','Request Field Inspection','Notify Monitoring Point','Generate Community Advisory','Mark Under Control']:
            response=client.post(f'/api/admin/reports/{rid}/actions',json={'action':action},headers=auth)
            assert response.status_code==201,response.text
            assert response.json()['details']['simulated'] is True
        assert len(client.get(f'/api/admin/reports/{rid}/actions').json())==6
        saved=client.get(f'/api/reports/{rid}').json()
        assert saved['image_urls']==urls and saved['timeline'][:len(original)]==original
        assert len(saved['timeline'])==len(original)+6
        assert client.patch(f'/api/reports/{rid}/status',json={'status':'RESOLVED'},headers=auth).status_code==200
    with TestClient(app) as client:
        assert client.get(f'/api/reports/{rid}').json()['image_urls']==urls

def test_image_limits_large_files_invalid_types_and_bad_references():
    with TestClient(app) as client:
        assert client.get('/api/config').json()['max_images_per_report']==MAX_IMAGES_PER_REPORT
        assert client.post('/api/uploads',files={'file':('large.png',b'x'*(5*1024*1024+1),'image/png')}).status_code==413
        assert client.post('/api/uploads',files={'file':('bad.webp',b'fake','image/webp')}).status_code==422
        body={'latitude':10.1253,'longitude':76.418,'contamination_type':'Dead Fish','description':'Test observation with invalid image references.','observed_at':(now()-timedelta(minutes=2)).isoformat(),'image_urls':[f'/uploads/{i}.jpg' for i in range(MAX_IMAGES_PER_REPORT+1)]}
        assert client.post('/api/reports',json=body).status_code==422
        body['image_urls']=['/uploads/nonexistent.jpg']
        assert client.post('/api/reports',json=body).status_code==422
