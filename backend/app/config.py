import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
IS_VERCEL = os.getenv('VERCEL') == '1'
DATA_DIR = Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve()
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(ROOT / 'uploads'))).resolve()
DATABASE_URL = next((os.getenv(key) for key in ('DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'NEON_DATABASE_URL') if os.getenv(key)), '')
DATABASE_CONFIGURED = bool(DATABASE_URL)
if not DATABASE_URL:
    DATABASE_URL = f'sqlite:///{ROOT / "data" / "riverguard.db"}' if not IS_VERCEL else 'sqlite:////tmp/riverguard.db'
if DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL.split('://', 1)[1]
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'vercel_blob' if IS_VERCEL else 'local')
if STORAGE_BACKEND not in {'local', 'vercel_blob'}:
    raise RuntimeError('STORAGE_BACKEND must be local or vercel_blob.')
PERSISTENT_DATABASE = DATABASE_URL.startswith('postgresql+psycopg://')
PERSISTENCE_MODE = 'postgres' if PERSISTENT_DATABASE else ('sqlite-temp' if IS_VERCEL else 'sqlite-local')
BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN', '')
PERSISTENT_STORAGE = IS_VERCEL and STORAGE_BACKEND == 'vercel_blob' and bool(BLOB_READ_WRITE_TOKEN)
if IS_VERCEL and not PERSISTENT_STORAGE:
    UPLOAD_DIR = Path('/tmp/riverguard-uploads')
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
