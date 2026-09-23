"""Prototype admin authentication: persisted opaque sessions and CSRF checks."""
import hashlib
import secrets
import time
from datetime import timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete
from . import config
from .database import get_db
from .models import AdminSession, now

router = APIRouter(prefix='/api/admin', tags=['Admin authentication'])
COOKIE = 'riverguard_admin'
attempts = {}

def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()

def check_origin(request):
    origin = request.headers.get('origin')
    allowed = {str(request.base_url).rstrip('/'), *config.CORS_ORIGINS}
    if origin and origin not in allowed:
        raise HTTPException(403, 'Untrusted request origin')

def require_admin(request: Request, db=Depends(get_db)):
    session = db.get(AdminSession, digest(request.cookies.get(COOKIE, '')))
    if not session or session.expires_at.replace(tzinfo=timezone.utc) <= now():
        raise HTTPException(401, 'Admin login required')
    if request.method not in ['GET', 'HEAD', 'OPTIONS']:
        check_origin(request)
        if not secrets.compare_digest(request.headers.get('x-csrf-token',''), session.csrf_token):
            raise HTTPException(403, 'Invalid session token. Please sign in again.')
    return session

class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)

@router.post('/login')
def login(payload: LoginInput, request: Request, response: Response, db=Depends(get_db)):
    check_origin(request)
    ip = request.client.host if request.client else 'unknown'
    timestamp = time.monotonic()
    recent = [t for t in attempts.get(ip,[]) if timestamp-t < 60]
    attempts[ip] = recent
    if len(recent) >= 10:
        raise HTTPException(429, 'Too many login attempts. Try again in a minute.')
    valid_user = secrets.compare_digest(payload.username.encode(), config.ADMIN_USERNAME.encode())
    valid_password = secrets.compare_digest(payload.password.encode(), config.ADMIN_PASSWORD.encode())
    if not (valid_user and valid_password):
        recent.append(timestamp)
        raise HTTPException(401, 'Invalid username or password.')
    attempts.pop(ip,None)
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now()))
    old = db.get(AdminSession, digest(request.cookies.get(COOKIE,'')))
    if old:
        db.delete(old)
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_hex(32)
    db.add(AdminSession(token_hash=digest(token),username=payload.username,csrf_token=csrf,expires_at=now()+timedelta(hours=config.SESSION_HOURS)))
    db.commit()
    response.set_cookie(COOKIE, token, max_age=config.SESSION_HOURS*3600, httponly=True, secure=config.COOKIE_SECURE, samesite='strict', path='/api')
    return {'username':payload.username,'csrf_token':csrf}

@router.get('/session')
def session(admin=Depends(require_admin)):
    return {'username':admin.username,'csrf_token':admin.csrf_token}

@router.post('/logout')
def logout(response: Response, admin=Depends(require_admin), db=Depends(get_db)):
    db.delete(admin)
    db.commit()
    response.delete_cookie(COOKIE, path='/api', httponly=True, secure=config.COOKIE_SECURE, samesite='strict')
    return {'message':'Signed out'}
