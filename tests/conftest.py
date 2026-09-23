import os
import tempfile
from pathlib import Path
import pytest

TEMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(TEMP.name) / 'test.db')
os.environ['UPLOAD_DIR'] = str(Path(TEMP.name) / 'uploads')
os.environ['AUTHORITY_API_KEY'] = 'test-secret'
os.environ['DATA_DIR'] = str(Path(__file__).resolve().parent/'fixtures'/'demo')
os.environ['ADMIN_USERNAME']='admin123'
os.environ['ADMIN_PASSWORD']='admin@123'

@pytest.fixture(autouse=True)
def isolated_database():
    from backend.app.database import Base, engine
    assert TEMP.name in str(engine.url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

@pytest.fixture(scope='session', autouse=True)
def close_database():
    yield
    from backend.app.database import engine
    engine.dispose()
    TEMP.cleanup()
