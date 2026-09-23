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
