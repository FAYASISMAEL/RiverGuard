"""Fetch Periyar river ways through OSM's read API when Overpass is busy.

Walk river-way endpoints (not proximity). This is a bounded API import, cached
locally, with every source response retained. No map edits are performed.
"""
import json
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'data/source'
CACHE=ROOT/'api-cache';CACHE.mkdir(exist_ok=True)
HEADERS={'User-Agent':'RiverGuardPrototype/1.0 (Periyar data import)'}

def fetch(kind,identifier,suffix):
    target=CACHE/f'{kind}-{identifier}-{suffix}.json'
    if target.exists():return json.loads(target.read_text(encoding='utf-8'))
    url=f'https://www.openstreetmap.org/api/0.6/{kind}/{identifier}/{suffix}.json'
    with urllib.request.urlopen(urllib.request.Request(url,headers=HEADERS),timeout=30) as response:
        result=json.load(response)
    target.write_text(json.dumps(result),encoding='utf-8')
    return result

def main():
    original=json.loads((ROOT/'periyar_relation.json').read_text(encoding='utf-8'))['elements']
    ways={e['id']:e for e in original if e['type']=='way'}
    all_elements={(e['type'],e['id']):e for e in original}
    # Published OSM confluence nodes along the Periyar, plus every mainstem endpoint.
    pending={4723547568,1905138287,1745142167,2136225413,4896668835,5830419849,1905138178}
    pending.update(n for w in ways.values() for n in (w['nodes'][0],w['nodes'][-1]))
    visited=set()
    while pending:
        node=pending.pop()
        if node in visited:continue
        visited.add(node)
        result=fetch('node',node,'ways')
        for way in result['elements']:
            if way['id'] in ways or way.get('tags',{}).get('waterway')!='river':continue
            full=fetch('way',way['id'],'full')
            for e in full['elements']:all_elements[(e['type'],e['id'])]=e
            ways[way['id']]=way
            pending.update(n for n in (way['nodes'][0],way['nodes'][-1]) if n not in visited)
        if len(visited)%10==0:print(f'{len(visited)} junctions, {len(ways)} river ways',flush=True)
        if len(visited)>250:raise RuntimeError('Review import coverage before walking more than 250 junctions')
    data={'version':0.6,'generator':'RiverGuard OSM API river connectivity import','elements':list(all_elements.values())}
    (ROOT/'waterways.json').write_text(json.dumps(data),encoding='utf-8')
    print(f'Saved {len(ways)} river ways from {len(visited)} junctions',flush=True)

if __name__=='__main__':main()
