from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DATABASE_URL

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, **(
    {'connect_args': {'check_same_thread': False}} if DATABASE_URL.startswith('sqlite')
    else {'poolclass': NullPool, 'connect_args': {'connect_timeout': 10}}
))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

def initialize_database():
    with engine.begin() as connection:
        # Serialize additive schema initialization across cold function instances.
        if connection.dialect.name == 'postgresql':
            connection.execute(text('SELECT pg_advisory_xact_lock(72418301)'))
        Base.metadata.create_all(connection)

def get_db():
    with SessionLocal() as session:
        yield session
