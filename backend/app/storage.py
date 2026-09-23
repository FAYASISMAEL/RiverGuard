"""Stable evidence URLs backed by local files or durable Vercel Blob objects."""
import logging
import re
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from . import config
from .models import UploadedAsset


def valid_name(name: str) -> bool:
    return bool(re.fullmatch(r'[a-f0-9]{32}\.jpg', name))


def save_evidence(name: str, content: bytes, db) -> str:
    url = '/uploads/' + name
    try:
        if config.STORAGE_BACKEND == 'vercel_blob':
            if not config.BLOB_READ_WRITE_TOKEN:
                raise RuntimeError('BLOB_READ_WRITE_TOKEN is missing')
            from vercel.blob import BlobClient
            with BlobClient(token=config.BLOB_READ_WRITE_TOKEN) as client:
                blob = client.put('evidence/' + name, content, access='public', content_type='image/jpeg')
                target = blob.url
        else:
            config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            (config.UPLOAD_DIR / name).write_bytes(content)
            target = url
    except Exception:
        logging.exception('Evidence storage failed')
        raise HTTPException(503, 'We could not store this photo right now. Please try again.') from None
    db.add(UploadedAsset(name=name, storage=config.STORAGE_BACKEND, url=target))
    db.commit()
    return url


def evidence_exists(url: str, db) -> bool:
    if not url.startswith('/uploads/'):
        return False
    name = url.removeprefix('/uploads/')
    if not valid_name(name):
        return False
    asset = db.get(UploadedAsset, name)
    if asset and asset.storage == 'vercel_blob':
        return True
    return config.STORAGE_BACKEND == 'local' and (config.UPLOAD_DIR / name).is_file()


def evidence_response(name: str, db):
    if not valid_name(name):
        raise HTTPException(404, 'Photo not found')
    asset = db.get(UploadedAsset, name)
    if asset and asset.storage == 'vercel_blob':
        return RedirectResponse(asset.url, status_code=307)
    if config.STORAGE_BACKEND == 'local' and (config.UPLOAD_DIR / name).is_file():
        return FileResponse(config.UPLOAD_DIR / name, media_type='image/jpeg')
    raise HTTPException(404, 'Photo not found')
