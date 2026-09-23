import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
IS_VERCEL = os.getenv('VERCEL') == '1'
DATA_DIR = Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve()
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(ROOT / 'uploads'))).resolve()
DATABASE_URL = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL') or os.getenv('NEON_DATABASE_URL') or f'sqlite:///{ROOT / "riverguard.db"}'
if DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL.split('://', 1)[1]
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'vercel_blob' if IS_VERCEL else 'local')
if STORAGE_BACKEND not in {'local', 'vercel_blob'}:
    raise RuntimeError('STORAGE_BACKEND must be local or vercel_blob.')
if IS_VERCEL and not DATABASE_URL.startswith('postgresql+psycopg://'):
    raise RuntimeError('Connect a PostgreSQL database and set DATABASE_URL before deploying to Vercel.')
if IS_VERCEL and STORAGE_BACKEND != 'vercel_blob':
    raise RuntimeError('Vercel requires STORAGE_BACKEND=vercel_blob for persistent evidence.')
BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN', '')
# Leave room for multipart headers below Vercel's 4.5 MB request limit.
MAX_IMAGE_BYTES = (4 if IS_VERCEL else 5) * 1024 * 1024
PROXIMITY_M = float(os.getenv('RIVER_PROXIMITY_M', '500'))
CORRIDOR_M = float(os.getenv('ASSET_CORRIDOR_M', '300'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin123')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin@123')
SESSION_HOURS = int(os.getenv('ADMIN_SESSION_HOURS', '8'))
COOKIE_SECURE = IS_VERCEL or os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
MAX_IMAGES_PER_REPORT = max(1, int(os.getenv('MAX_IMAGES_PER_REPORT', '5')))
CORS_ORIGINS = [origin.strip().rstrip('/') for origin in os.getenv(
    'CORS_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174'
).split(',') if origin.strip()]
if IS_VERCEL:
    for key in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL'):
        domain = os.getenv(key, '').strip()
        if domain:
            CORS_ORIGINS.append('https://' + domain)
