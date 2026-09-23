"""Vercel ASGI entrypoint; all API and evidence requests use the existing app."""
from backend.app.main import app
