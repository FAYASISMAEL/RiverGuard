import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DATA_DIR = Path(os.getenv('DATA_DIR', str(ROOT / 'data'))).resolve()
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', str(ROOT / 'uploads'))).resolve()
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{ROOT / "riverguard.db"}')
PROXIMITY_M = float(os.getenv('RIVER_PROXIMITY_M', '500'))
CORRIDOR_M = float(os.getenv('ASSET_CORRIDOR_M', '300'))
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin123')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin@123')
SESSION_HOURS = int(os.getenv('ADMIN_SESSION_HOURS', '8'))
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
MAX_IMAGES_PER_REPORT = max(1, int(os.getenv('MAX_IMAGES_PER_REPORT', '5')))
CORS_ORIGINS = [origin.strip().rstrip('/') for origin in os.getenv(
    'CORS_ORIGINS',
    'http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174'
).split(',') if origin.strip()]
