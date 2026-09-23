"""Local simulation: built SPA + real ASGI API. Never used in Vercel runtime."""
from pathlib import Path
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, JSONResponse
from api.server import app as backend

DIST = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
assets = StaticFiles(directory=DIST/'assets')

async def app(scope, receive, send):
    path = scope.get('path', '')
    if scope['type'] == 'lifespan' or path.startswith(('/api/', '/uploads/')) or path in ('/docs','/openapi.json'):
        await backend(scope, receive, send)
    elif path.startswith('/assets/'):
        child = dict(scope, path=path.removeprefix('/assets'))
        await assets(child, receive, send)
    elif scope['type'] == 'http' and scope['method'] in ('GET','HEAD'):
        await FileResponse(DIST/'index.html')(scope, receive, send)
    else:
        await JSONResponse({'detail':'Not found'},status_code=404)(scope, receive, send)
