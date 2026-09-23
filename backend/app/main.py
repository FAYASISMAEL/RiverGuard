import logging
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from io import BytesIO
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from . import config
from .database import Base, engine as db_engine, get_db
from .models import Report, Alert, now
from .schemas import Location, ReportInput, StatusInput, AlertInput
from .river_impact_engine import RiverImpactEngine
from .river_impact_engine.snap_engine import ProximityError
from .services import create_report, serialize, repeats, generate_alerts, event

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources at startup and release them on shutdown."""
    Base.metadata.create_all(db_engine)
    application.state.river = None
    try:
        application.state.river = RiverImpactEngine(config.DATA_DIR, config.PROXIMITY_M, config.CORRIDOR_M)
    except Exception:
        logging.exception('Dataset could not be loaded. Correct DATA_DIR and restart.')
    try:
        yield
    finally:
        db_engine.dispose()

app = FastAPI(title='RiverGuard API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(','), allow_methods=['GET','POST','PATCH'], allow_headers=['Content-Type','X-Authority-Key'])
config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount('/uploads', StaticFiles(directory=config.UPLOAD_DIR), name='uploads')

def river():
    if app.state.river is None:
        raise HTTPException(503, 'River datasets unavailable. Check DATA_DIR and restart the backend.')
    return app.state.river

def authority(x_authority_key: str = Header(default='')):
    key = os.getenv('AUTHORITY_API_KEY', '')
    if key and not secrets.compare_digest(key, x_authority_key):
        raise HTTPException(403, 'An authority key is required.')

def find_report(db, report_id):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, 'Report not found')
    return report

@app.exception_handler(ProximityError)
async def proximity_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={'detail': str(exc)})

@app.get('/api/health')
def health():
    return {'status':'ok' if app.state.river else 'degraded', 'datasets_available':app.state.river is not None, 'authority_mode':'key' if os.getenv('AUTHORITY_API_KEY') else 'demo'}

@app.get('/api/map/{layer}')
def map_layer(layer: str, gis=Depends(river)):
    key = {'river':'river_network','intakes':'water_intakes','monitoring-points':'monitoring_points','local-bodies':'local_bodies','settlements':'settlements'}.get(layer)
    if not key:
        raise HTTPException(404, 'Unknown map layer')
    return gis.datasets[key]

@app.post('/api/analyze')
def analyze(payload: Location, db=Depends(get_db), gis=Depends(river)):
    snap = gis.snap_engine.snap(payload.latitude, payload.longitude)
    return gis.analyze(payload.latitude, payload.longitude, repeats(db, snap['segment_id']))

@app.post('/api/uploads', status_code=201)
async def upload(file: UploadFile):
    content = await file.read(5*1024*1024+1)
    if len(content) > 5*1024*1024:
        raise HTTPException(413, 'Image must be smaller than 5 MB')
    try:
        with Image.open(BytesIO(content)) as picture:
            if picture.format not in ['JPEG','PNG','WEBP'] or picture.width*picture.height > 20_000_000:
                raise ValueError()
            picture.load()
            name = uuid4().hex+'.jpg'
            picture.convert('RGB').save(config.UPLOAD_DIR/name, 'JPEG', quality=85)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, 'Choose a valid JPEG, PNG or WebP image under 20 megapixels')
    return {'image_url':'/uploads/'+name}

@app.post('/api/reports', status_code=201)
def submit(payload: ReportInput, db=Depends(get_db), gis=Depends(river)):
    if payload.image_url:
        name = payload.image_url.removeprefix('/uploads/')
        if payload.image_url != '/uploads/'+name or '/' in name or '\\' in name or not (config.UPLOAD_DIR/name).is_file():
            raise HTTPException(422, 'Image must be uploaded first')
    return serialize(create_report(db, gis, payload))

@app.get('/api/reports')
def reports(db=Depends(get_db)):
    return [serialize(r) for r in db.scalars(select(Report).order_by(Report.created_at.desc())).all()]

@app.get('/api/reports/{report_id}')
def report(report_id: str, db=Depends(get_db)):
    return serialize(find_report(db, report_id))

@app.get('/api/reports/{report_id}/impact')
def impact(report_id: str, db=Depends(get_db)):
    r = find_report(db, report_id)
    return {**r.impact, 'report_id':r.id, 'status':r.status}

@app.patch('/api/reports/{report_id}/status', dependencies=[Depends(authority)])
def status(report_id: str, payload: StatusInput, db=Depends(get_db)):
    r = find_report(db, report_id)
    allowed = {'UNVERIFIED':['UNDER REVIEW','VERIFIED','REJECTED'], 'UNDER REVIEW':['VERIFIED','REJECTED'], 'VERIFIED':['RESOLVED'], 'REJECTED':[], 'RESOLVED':[]}
    if payload.status not in allowed[r.status]:
        raise HTTPException(409, f'Cannot change {r.status} to {payload.status}')
    r.status = payload.status
    r.timeline = [*r.timeline, event('Authority review: '+payload.status, payload.note)]
    db.commit()
    return serialize(r)

@app.get('/api/reports/{report_id}/alerts')
def alerts(report_id: str, db=Depends(get_db)):
    find_report(db, report_id)
    return db.scalars(select(Alert).where(Alert.report_id == report_id)).all()

@app.post('/api/reports/{report_id}/alerts', dependencies=[Depends(authority)])
def create_alerts(report_id: str, db=Depends(get_db)):
    r = find_report(db, report_id)
    result = generate_alerts(db, r)
    db.commit()
    return result

@app.patch('/api/alerts/{alert_id}', dependencies=[Depends(authority)])
def update_alert(alert_id: str, payload: AlertInput, db=Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, 'Alert not found')
    if (alert.state, payload.state) not in [('Generated','Sent - Simulated'),('Sent - Simulated','Acknowledged')]:
        raise HTTPException(409, 'Invalid alert transition')
    alert.state = payload.state
    r = find_report(db, alert.report_id)
    r.timeline = [*r.timeline, event('Alert '+payload.state, alert.target)]
    db.commit()
    return alert

@app.get('/api/hotspots')
def hotspots(db=Depends(get_db)):
    groups = {}
    for r in db.scalars(select(Report)).all():
        g = groups.setdefault(r.segment_id, {'segment_id':r.segment_id,'total':0,'last_30_days':0})
        g['total'] += 1
        if r.created_at.replace(tzinfo=now().tzinfo) >= now()-timedelta(days=30):
            g['last_30_days'] += 1
    return [{**g,'frequency':'HIGH FREQUENCY' if g['last_30_days'] >= 5 else 'MODERATE' if g['last_30_days'] >= 2 else 'LOW'} for g in groups.values()]

@app.post('/api/demo', status_code=201)
def demo(db=Depends(get_db), gis=Depends(river)):
    return serialize(create_report(db, gis, ReportInput(latitude=10.1253, longitude=76.418, contamination_type='Industrial Discharge', description='DEMO: unusual dark discharge observed near the riverbank. Requires authority verification.', observed_at=now()-timedelta(minutes=15))))
