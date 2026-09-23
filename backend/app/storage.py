"""Stable evidence URLs backed by local files or durable Vercel Blob objects."""
import logging
import re
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from . import config
from .models import UploadedAsset
from .diagnostics import log_failure

class LocalStorageAdapter:
    storage_name = 'temp-local'

    def __init__(self, directory):
        self.directory = directory

    def save_file(self, name, content):
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / name).write_bytes(content)
        return '/uploads/' + name


class BlobStorageAdapter:
    storage_name = 'vercel_blob'

    def __init__(self, token):
        self.token = token

    def save_file(self, name, content):
        from vercel.blob import BlobClient
        with BlobClient(token=self.token) as client:
            blob = client.put('evidence/' + name, content, access='public', content_type='image/jpeg')
        return blob.url


def storage_adapter():
    if config.STORAGE_BACKEND == 'vercel_blob' and config.BLOB_READ_WRITE_TOKEN:
        return BlobStorageAdapter(config.BLOB_READ_WRITE_TOKEN)
    if not config.IS_VERCEL and config.STORAGE_BACKEND == 'local':
        return LocalStorageAdapter(config.UPLOAD_DIR)
    raise HTTPException(503, 'Photo storage is unavailable. Connect a public Vercel Blob store and set BLOB_READ_WRITE_TOKEN. Your report has not been submitted.')


def valid_name(name: str) -> bool:
    return bool(re.fullmatch(r'[a-f0-9]{32}\.jpg', name))


def save_evidence(name: str, content: bytes, db) -> str:
    url = '/uploads/' + name
    adapter = storage_adapter()
    storage = adapter.storage_name
    try:
        target = adapter.save_file(name, content)
        if storage == 'temp-local' and not config.IS_VERCEL:
            storage = 'local'
    except Exception as exc:
        log_failure('Evidence storage failed', exc)
        raise HTTPException(503, 'We could not store this photo right now. Please try again.') from None
    db.add(UploadedAsset(name=name, storage=storage, url=target))
    db.commit()
    return url


def evidence_exists(url: str, db) -> bool:
    if not url.startswith('/uploads/'):
        return False
    name = url.removeprefix('/uploads/')
    if not valid_name(name):
        return False
    asset = db.get(UploadedAsset, name)
    if asset:
        if asset.storage == 'vercel_blob':
            return True
        return (config.UPLOAD_DIR / name).is_file()
    # Preserve images uploaded before the additive registry table was introduced.
    return not config.IS_VERCEL and config.STORAGE_BACKEND == 'local' and (config.UPLOAD_DIR / name).is_file()


def evidence_response(name: str, db):
    if not valid_name(name):
        raise HTTPException(404, 'Photo not found')
    asset = db.get(UploadedAsset, name)
    if asset and asset.storage == 'vercel_blob':
        return RedirectResponse(asset.url, status_code=307)
    if not config.IS_VERCEL and (config.UPLOAD_DIR / name).is_file():
        return FileResponse(config.UPLOAD_DIR / name, media_type='image/jpeg')
    raise HTTPException(404, 'Photo not found')
