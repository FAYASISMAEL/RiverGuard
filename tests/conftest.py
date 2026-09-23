import os
import tempfile
from pathlib import Path
import pytest

TEMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(TEMP.name) / 'test.db')
os.environ['UPLOAD_DIR'] = str(Path(TEMP.name) / 'uploads')
os.environ['AUTHORITY_API_KEY'] = 'test-secret'

@pytest.fixture(scope='session', autouse=True)
def close_database():
    yield
    from backend.app.database import engine
    engine.dispose()
    TEMP.cleanup()
