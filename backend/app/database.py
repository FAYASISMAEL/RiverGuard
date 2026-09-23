import logging
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from . import config

class Base(DeclarativeBase):
    pass

def make_engine(url):
    return create_engine(url, **(
    {'connect_args': {'check_same_thread': False}} if url.startswith('sqlite')
    else {'poolclass': NullPool, 'connect_args': {'connect_timeout': 10}}
    ))

engine = make_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def switch_to_sqlite():
    global engine, SessionLocal
    fallback = ('sqlite:////tmp/riverguard.db' if config.IS_VERCEL
                else f'sqlite:///{config.ROOT / "data" / "riverguard.db"}')
    engine.dispose()
    engine = make_engine(fallback)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    config.DATABASE_URL = fallback
    config.PERSISTENT_DATABASE = False
    config.PERSISTENCE_MODE = 'sqlite-temp' if config.IS_VERCEL else 'sqlite-local'

def initialize_database():
    try:
        with engine.begin() as connection:
            if connection.dialect.name == 'postgresql':
                connection.execute(text('SELECT pg_advisory_xact_lock(72418301)'))
            Base.metadata.create_all(connection)
    except Exception:
        if engine.url.drivername.startswith('sqlite'):
            raise
        logging.warning('PostgreSQL unavailable; falling back to SQLite persistence.')
        switch_to_sqlite()
        with engine.begin() as connection:
            Base.metadata.create_all(connection)
        return False
    return True

def get_db():
    with SessionLocal() as session:
        yield session


def get_db_optional():
    with SessionLocal() as session:
        yield session
