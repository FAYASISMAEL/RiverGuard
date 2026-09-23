"""Database availability must never prevent importing or using the river engine."""
import logging
import time
from threading import Lock
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from . import config
from .diagnostics import log_failure

class Base(DeclarativeBase):
    pass

def make_engine(url):
    if not url or (config.IS_VERCEL and not url.startswith('postgresql+psycopg://')):
        return None
    try:
        return create_engine(url, **(
            {'connect_args': {'check_same_thread': False}} if url.startswith('sqlite')
            else {'poolclass': NullPool, 'hide_parameters': True, 'connect_args': {'connect_timeout': 5}}
        ))
    except Exception as exc:
        log_failure('Database configuration unavailable', exc)
        return None

engine = make_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
_ready = False
_retry_after = 0.0
_lock = Lock()

def initialize_database():
    global _ready, _retry_after
    if _ready:
        return True
    if engine is None or time.monotonic() < _retry_after:
        return False
    with _lock:
        if _ready:
            return True
        if time.monotonic() < _retry_after:
            return False
        try:
            with engine.begin() as connection:
                if connection.dialect.name == 'postgresql':
                    connection.execute(text('SELECT pg_advisory_xact_lock(72418301)'))
                Base.metadata.create_all(connection)
            _ready = True
            logging.info('Database initialized')
            return True
        except Exception as exc:
            _retry_after = time.monotonic() + 30
            log_failure('Database unavailable; map and analysis remain available', exc)
            return False

def database_status():
    if not initialize_database():
        return 'unavailable'
    try:
        with SessionLocal() as session:
            session.execute(text('SELECT 1'))
        return 'connected'
    except Exception as exc:
        log_failure('Database health check failed', exc)
        return 'unavailable'

def get_db():
    if not initialize_database():
        raise HTTPException(503, 'Database unavailable. Reports and admin sessions require a working DATABASE_URL. The river map remains available.')
    with SessionLocal() as session:
        yield session

def get_db_optional():
    if not initialize_database():
        yield None
        return
    with SessionLocal() as session:
        yield session
