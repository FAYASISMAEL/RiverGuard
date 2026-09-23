import logging
from threading import Lock
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from io import BytesIO
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from . import config
from . import database
from .database import get_db, get_db_optional, initialize_database
from .storage import save_evidence, evidence_exists, evidence_response
from .models import Report, Alert, now
from .schemas import Location, ReportInput, StatusInput, AlertInput
from .river_impact_engine import RiverImpactEngine
from .river_impact_engine.snap_engine import ProximityError
from .services import create_report, serialize, repeats, generate_alerts, event, change_status
from .auth import require_admin as authority, router as auth_router
from .admin import router as admin_router

_startup_lock = Lock()

def initialize_runtime(application: FastAPI, force: bool = False):
    with _startup_lock:
        if not force and getattr(application.state, 'initialized', False):
            return
        application.state.river = None
        try:
            application.state.river = RiverImpactEngine(config.DATA_DIR, config.PROXIMITY_M, config.CORRIDOR_M)
        except Exception:
            logging.exception('Dataset could not be loaded. Correct DATA_DIR and restart.')
        application.state.database_available = False
        try:
            initialize_database()
            application.state.database_available = True
        except Exception:
            logging.exception('Database could not be initialized. Database-backed routes are unavailable.')
        application.state.persistence_mode = config.PERSISTENCE_MODE
        application.state.storage_mode = 'blob' if config.PERSISTENT_STORAGE else ('temp-local' if config.IS_VERCEL else 'local')
        application.state.initialized = True

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources at startup and release them on shutdown."""
    await run_in_threadpool(initialize_runtime, application, True)
    try:
        yield
    finally:
        database.engine.dispose()

app = FastAPI(title='RiverGuard API', version='1.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=True, allow_methods=['GET','POST','PATCH'], allow_headers=['Content-Type','X-CSRF-Token'])
app.include_router(auth_router)
app.include_router(admin_router)

@app.middleware('http')
async def serverless_startup(request, call_next):
    # File-based ASGI runtimes may not send lifespan events. Initialize once per
    # warm instance without opening a database connection during build imports.
    if config.IS_VERCEL and not getattr(app.state, 'initialized', False):
        try:
            await run_in_threadpool(initialize_runtime, app)
        except Exception:
            logging.exception('Cloud startup failed')
            return JSONResponse(status_code=503, content={'detail':'The service could not start. Please try again shortly.'})
    return await call_next(request)

@app.get('/uploads/{name}', include_in_schema=False)
def evidence(name: str, db=Depends(get_db)):
    return evidence_response(name, db)

def river():
    if app.state.river is None:
        raise HTTPException(503, 'River datasets unavailable. Check DATA_DIR and restart the backend.')
    return app.state.river

def find_report(db, report_id):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(404, 'Report not found')
    return report

@app.exception_handler(ProximityError)
async def proximity_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=422, content={'detail': str(exc)})

@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    from fastapi.responses import JSONResponse
    logging.error('Database operation failed', exc_info=(type(exc), exc, exc.__traceback__))
    message = 'Persistence service is temporarily unavailable. Map and river analysis remain available.'
    return JSONResponse(status_code=503, content={'success':False, 'code':'DATABASE_UNAVAILABLE', 'message':message, 'detail':message})

@app.get('/api/config')
def public_config():
    return {'max_images_per_report':config.MAX_IMAGES_PER_REPORT,'max_image_bytes':config.MAX_IMAGE_BYTES,'accepted_image_types':['image/jpeg','image/png','image/webp']}

@app.get('/api/health')
def health():
    map_available = app.state.river is not None
    database_available = getattr(app.state, 'database_available', False)
    return {
        'status': 'ok' if map_available and database_available else 'degraded',
        'datasets_available': map_available,
        'map_service': 'available' if map_available else 'unavailable',
        'river_engine': 'available' if map_available else 'unavailable',
        'database': 'available' if database_available else 'unavailable',
        'storage': getattr(app.state, 'storage_mode', 'unknown'),
        'persistence_mode': getattr(app.state, 'persistence_mode', config.PERSISTENCE_MODE),
        'authority_mode':'admin-login'
    }

@app.get('/api/map-metadata')
def map_metadata(gis=Depends(river)):
    return gis.metadata

@app.get('/api/map/{layer}')
def map_layer(layer: str, gis=Depends(river)):
    key = {'river':'river_network','intakes':'water_intakes','monitoring-points':'monitoring_points','local-bodies':'local_bodies','settlements':'settlements'}.get(layer)
    if not key:
        raise HTTPException(404, 'Unknown map layer')
    return gis.datasets[key]

@app.post('/api/analyze')
def analyze(payload: Location, db=Depends(get_db_optional), gis=Depends(river)):
    snap = gis.snap_engine.snap(payload.latitude, payload.longitude)
    repeat_count = 0
    if db is not None:
        try:
            repeat_count = repeats(db, snap['segment_id'])
        except SQLAlchemyError:
            logging.warning('Report history unavailable; analyzing without repeat history.')
    return gis.analyze(payload.latitude, payload.longitude, repeat_count)

@app.post('/api/uploads', status_code=201)
def upload(file: UploadFile, db=Depends(get_db)):
    content = file.file.read(config.MAX_IMAGE_BYTES+1)
    if len(content) > config.MAX_IMAGE_BYTES:
        raise HTTPException(413, f'Image must be smaller than {config.MAX_IMAGE_BYTES // (1024*1024)} MB')
    try:
        with Image.open(BytesIO(content)) as picture:
            if picture.format not in ['JPEG','PNG','WEBP'] or picture.width*picture.height > 20_000_000:
                raise ValueError()
            picture.load()
            name = uuid4().hex+'.jpg'
            output = BytesIO()
            picture.convert('RGB').save(output, 'JPEG', quality=85)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, 'Choose a valid JPEG, PNG or WebP image under 20 megapixels')
    return {'image_url':save_evidence(name, output.getvalue(), db)}

@app.post('/api/reports', status_code=201)
def submit(payload: ReportInput, db=Depends(get_db), gis=Depends(river)):
    images=list(dict.fromkeys(([payload.image_url] if payload.image_url else [])+payload.image_urls))
    if len(images)>config.MAX_IMAGES_PER_REPORT:
        raise HTTPException(422, f'Please attach no more than {config.MAX_IMAGES_PER_REPORT} images.')
    for url in images:
        if not evidence_exists(url, db):
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
def status(report_id: str, payload: StatusInput, db=Depends(get_db), admin=Depends(authority)):
    r = find_report(db, report_id)
    try:
        return serialize(change_status(db, r, payload.status, payload.note, admin.username))
    except ValueError as exc:
        raise HTTPException(409, str(exc))

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
    point = gis.metadata.get('demo_location', {'latitude':10.1253, 'longitude':76.418})
    return serialize(create_report(db, gis, ReportInput(**point, contamination_type='Industrial Discharge', description='DEMO: unusual dark discharge observed near the riverbank. Requires authority verification.', observed_at=now()-timedelta(minutes=15))))
