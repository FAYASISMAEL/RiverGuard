import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_config(monkeypatch, **env):
    for key in ['VERCEL', 'DATABASE_URL', 'POSTGRES_URL', 'POSTGRES_PRISMA_URL', 'NEON_DATABASE_URL', 'STORAGE_BACKEND', 'COOKIE_SECURE', 'VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL']:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    # Import an independent config module, leaving the running test DB untouched.
    spec = importlib.util.spec_from_file_location('deployment_config_test', ROOT/'backend/app/config.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_vercel_uses_persistent_database_secure_cookie_and_exact_origins(monkeypatch):
    config = load_config(monkeypatch, VERCEL='1', DATABASE_URL='postgres://test:password@localhost/db?sslmode=require', VERCEL_URL='riverguard-abc.vercel.app', VERCEL_PROJECT_PRODUCTION_URL='riverguard.vercel.app', COOKIE_SECURE='false')
    assert config.DATABASE_URL == 'postgresql+psycopg://test:password@localhost/db?sslmode=require'
    assert config.COOKIE_SECURE is True
    assert config.STORAGE_BACKEND == 'vercel_blob'
    assert config.MAX_IMAGE_BYTES == 4*1024*1024
    assert 'https://riverguard-abc.vercel.app' in config.CORS_ORIGINS
    assert 'https://riverguard.vercel.app' in config.CORS_ORIGINS
    assert 'https://unrelated.vercel.app' not in config.CORS_ORIGINS


def test_vercel_accepts_neon_pooled_database_variable(monkeypatch):
    config = load_config(monkeypatch, VERCEL='1', POSTGRES_URL='postgresql://test:password@localhost/db?sslmode=require')
    assert config.DATABASE_URL == 'postgresql+psycopg://test:password@localhost/db?sslmode=require'


def test_vercel_accepts_neon_prisma_database_variable(monkeypatch):
    config = load_config(monkeypatch, VERCEL='1', POSTGRES_PRISMA_URL='postgresql://test:password@localhost/db?sslmode=require')
    assert config.DATABASE_URL == 'postgresql+psycopg://test:password@localhost/db?sslmode=require'


def test_vercel_uses_temporary_database_fallback_when_postgres_is_missing(monkeypatch):
    config = load_config(monkeypatch, VERCEL='1', DATABASE_URL='sqlite:////tmp/riverguard.db')
    assert config.DATABASE_URL == 'sqlite:////tmp/riverguard-fallback.db'
    assert config.PERSISTENT_DATABASE is False


def test_vercel_uses_temporary_upload_fallback_when_blob_is_missing(monkeypatch):
    config = load_config(monkeypatch, VERCEL='1', DATABASE_URL='postgresql://test:password@localhost/db', STORAGE_BACKEND='local')
    assert config.UPLOAD_DIR == Path('/tmp/riverguard-uploads')
    assert config.PERSISTENT_STORAGE is False


def test_vercel_build_targets_full_repository_and_api_before_spa():
    config = json.loads((ROOT/'vercel.json').read_text())
    assert config['outputDirectory'] == 'frontend/dist'
    assert config['rewrites'][0] == {'source': '/api/:path*', 'destination': '/api/server'}
    assert config['rewrites'][1] == {'source': '/uploads/:path*', 'destination': '/api/server'}
    assert (ROOT/'api/server.py').exists()
    assert (ROOT/'requirements.txt').exists()
