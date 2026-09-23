import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_config(monkeypatch, **env):
    for key in ['VERCEL', 'DATABASE_URL', 'STORAGE_BACKEND', 'COOKIE_SECURE', 'VERCEL_URL', 'VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL']:
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


def test_vercel_cannot_silently_use_ephemeral_sqlite(monkeypatch):
    with pytest.raises(RuntimeError, match='PostgreSQL'):
        load_config(monkeypatch, VERCEL='1', DATABASE_URL='sqlite:////tmp/riverguard.db')


def test_vercel_cannot_silently_use_ephemeral_uploads(monkeypatch):
    with pytest.raises(RuntimeError, match='persistent evidence'):
        load_config(monkeypatch, VERCEL='1', DATABASE_URL='postgresql://test:password@localhost/db', STORAGE_BACKEND='local')


def test_vercel_build_targets_full_repository_and_api_before_spa():
    config = json.loads((ROOT/'vercel.json').read_text())
    assert config['outputDirectory'] == 'frontend/dist'
    assert config['rewrites'][0] == {'source': '/api/:path*', 'destination': '/api/server'}
    assert config['rewrites'][1] == {'source': '/uploads/:path*', 'destination': '/api/server'}
    assert (ROOT/'api/server.py').exists()
    assert (ROOT/'requirements.txt').exists()
