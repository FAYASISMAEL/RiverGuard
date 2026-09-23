"""Download a bounded source extract; no invented geometry or snapped joins."""
import json
import gzip
import urllib.request
import urllib.parse
from pathlib import Path

query = '[out:json][timeout:120];way["waterway"="river"](9.1,76.1,10.6,77.55);out body geom;'
request = urllib.request.Request('https://overpass-api.de/api/interpreter', data=urllib.parse.urlencode({'data':query}).encode(), headers={'User-Agent':'RiverGuardPrototype/1.0 (Periyar river data preparation)', 'Accept-Encoding':'gzip'})
with urllib.request.urlopen(request, timeout=180) as response:
    content=response.read()
    data=json.loads(gzip.decompress(content) if response.headers.get('Content-Encoding')=='gzip' else content)
if data.get('remark'):
    raise RuntimeError(data['remark'])
target=Path(__file__).resolve().parents[1]/'data/source/waterways.json'
target.write_text(json.dumps(data),encoding='utf-8')
print(f'Saved {len(data["elements"])} source elements')
