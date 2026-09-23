"""One active persistence provider; river startup never requires a database."""
import logging
import time
from threading import Lock
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from . import config
from .diagnostics import log_failure

class Base(DeclarativeBase):
    pass


def make_engine(url):
    if not url:
        return None
    try:
        parsed = make_url(url)
        if parsed.get_backend_name() == 'sqlite':
            if config.IS_VERCEL and parsed.database != str(config.FALLBACK_DATABASE_PATH):
                return None
            if parsed.database and parsed.database != ':memory:':
                path = config.project_path(parsed.database, config.FALLBACK_DATABASE_PATH)
                path.parent.mkdir(parents=True, exist_ok=True)
                url = parsed.set(database=str(path))
            options = {'connect_args': {'check_same_thread': False, 'timeout': 5}}
        elif parsed.get_backend_name() == 'postgresql':
            options = {'poolclass': NullPool, 'hide_parameters': True, 'connect_args': {'connect_timeout': 5}}
        else:
            return None
        return create_engine(url, **options)
    except Exception as exc:
        log_failure('Database configuration unavailable', exc)
        return None


engine = make_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
_ready = False
_retry_after = 0.0
_lock = Lock()


def prepare(candidate):
    with candidate.begin() as connection:
        if connection.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_xact_lock(72418301)'))
        Base.metadata.create_all(connection)
        connection.execute(text('SELECT 1'))


def initialize_database():
    global engine, _ready, _retry_after
    # Keep fallback sticky for this instance: switching back would strand its
    # sessions and reports. A new instance tries the preferred database again.
    with _lock:
        if time.monotonic() < _retry_after:
            return False
        if engine is not None:
            try:
                if not _ready:
                    prepare(engine)
                else:
                    with engine.connect() as connection:
                        connection.execute(text('SELECT 1'))
                _ready = True
                return True
            except Exception as exc:
                log_failure('Active database unavailable; trying SQLite fallback', exc)
                engine.dispose()
                _ready = False
        candidate = make_engine('sqlite:///' + str(config.FALLBACK_DATABASE_PATH))
        try:
            if candidate is None:
                raise RuntimeError('SQLite engine unavailable')
            prepare(candidate)
            engine = candidate
            SessionLocal.configure(bind=engine)
            _ready = True
            logging.warning('SQLite fallback activated: %s', 'temporary instance storage' if config.IS_VERCEL else 'local storage')
            return True
        except Exception as exc:
            if candidate is not None:
                candidate.dispose()
            log_failure('All persistence options unavailable', exc)
            _retry_after = time.monotonic() + 30
            return False


def get_database_engine():
    return engine if initialize_database() else None


def database_status():
    active = get_database_engine()
    if active is None:
        return 'unavailable'
    if active.dialect.name == 'postgresql':
        return 'postgres'
    return 'sqlite-temp' if config.IS_VERCEL else 'sqlite-local'


def get_db():
    active = get_database_engine()
    if active is None:
        raise HTTPException(503, 'Report management is temporarily unavailable.')
    with SessionLocal(bind=active) as session:
        yield session


def get_db_optional():
    active = get_database_engine()
    if active is None:
        yield None
        return
    with SessionLocal(bind=active) as session:
        yield session
