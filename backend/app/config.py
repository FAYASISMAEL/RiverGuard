import os
import logging
import math
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
IS_VERCEL = bool(os.getenv('VERCEL'))
def project_path(value, default):
    path = Path(value or default)
    return (path if path.is_absolute() else ROOT / path).resolve()

DATA_DIR = project_path(os.getenv('DATA_DIR'), ROOT / 'data')
UPLOAD_DIR = Path('/tmp/riverguard-uploads') if IS_VERCEL else project_path(os.getenv('UPLOAD_DIR'), ROOT / 'uploads')
DATABASE_URL = next((value for key in ('DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'NEON_DATABASE_URL') if (value := os.getenv(key, '').strip())), '')
DATABASE_CONFIGURED = bool(DATABASE_URL)
FALLBACK_DATABASE_PATH = Path('/tmp/riverguard.db') if IS_VERCEL else ROOT / 'data' / 'riverguard.db'
if DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    DATABASE_URL = 'postgresql+psycopg://' + DATABASE_URL.split('://', 1)[1]
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'vercel_blob' if IS_VERCEL else 'local')
PERSISTENT_DATABASE = DATABASE_URL.startswith('postgresql+psycopg://') or (not IS_VERCEL and DATABASE_URL.startswith('sqlite'))
PERSISTENCE_MODE = 'postgres' if DATABASE_URL.startswith('postgresql+psycopg://') else ('sqlite-temp' if IS_VERCEL else 'sqlite-local')
BLOB_READ_WRITE_TOKEN = os.getenv('BLOB_READ_WRITE_TOKEN', '') or os.getenv('BLOB_TOKEN', '')
PERSISTENT_STORAGE = STORAGE_BACKEND == 'vercel_blob' and bool(BLOB_READ_WRITE_TOKEN)
# Leave room for multipart headers below Vercel's 4.5 MB request limit.
MAX_IMAGE_BYTES = (4 if IS_VERCEL else 5) * 1024 * 1024
def positive_setting(name, default, integer=False):
    try:
        value = int(os.getenv(name, str(default))) if integer else float(os.getenv(name, str(default)))
        if value <= 0 or not math.isfinite(value):
            raise ValueError()
        return value
    except ValueError:
        logging.warning('Invalid %s configuration; using its default', name)
        return default

PROXIMITY_M = positive_setting('RIVER_PROXIMITY_M', 500.0)
CORRIDOR_M = positive_setting('ASSET_CORRIDOR_M', 300.0)
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin123')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin@123')
SESSION_HOURS = int(positive_setting('ADMIN_SESSION_HOURS', 8, integer=True))
COOKIE_SECURE = IS_VERCEL or os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
MAX_IMAGES_PER_REPORT = min(50, int(positive_setting('MAX_IMAGES_PER_REPORT', 5, integer=True)))
CORS_ORIGINS = [origin.strip().rstrip('/') for origin in os.getenv(
    'CORS_ORIGINS', os.getenv('ALLOWED_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174'
)).split(',') if origin.strip()]
if IS_VERCEL:
    for key in ('VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL'):
        domain = os.getenv(key, '').strip()
        if domain:
            CORS_ORIGINS.append('https://' + domain)
