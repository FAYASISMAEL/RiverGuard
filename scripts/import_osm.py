"""Convert original OSM coordinates into directed, junction-split GeoJSON.

No synthetic connectors, geometry simplification, coordinate shifts or direction
inference. OSM way order specifies mapped flow direction. Inspect metadata for
source coverage and disconnected components before operational use.
"""
import json
import hashlib
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
import networkx as nx

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'

def main():
    relation=json.loads((DATA/'source/periyar_relation.json').read_text(encoding='utf-8'))
    extra=json.loads((DATA/'source/waterways.json').read_text(encoding='utf-8'))
    ways={};nodes={}
    for element in extra['elements']+relation['elements']:
        if element['type']=='node':
            nodes[element['id']]=[element['lon'],element['lat']]
        elif element['type']=='way' and element.get('tags',{}).get('waterway') in ['river','stream']:
            ways[element['id']]=element
            for identifier,coordinate in zip(element['nodes'],element.get('geometry',[])):
                nodes[identifier]=[coordinate['lon'],coordinate['lat']]
    members={m['ref'] for r in relation['elements'] if r['type']=='relation' for m in r['members'] if m['type']=='way'}
    # The southern Periyar outlet shares a node with Edakochi Kayal. Walking
    # through that separate backwater imports the Pamba/Manimala catchments.
    # Stop at this mapped outlet; never turn spatial proximity into a connector.
    excluded_connectors={613007375}
    ways={key:way for key,way in ways.items() if key not in excluded_connectors}
    graph=nx.Graph()
    for way in ways.values():
        graph.add_edges_from(zip(way['nodes'],way['nodes'][1:]))
    retained=set()
    for component in nx.connected_components(graph):
        if any(ways[w]['nodes'][0] in component for w in members if w in ways):
            retained.update(component)
    chosen=[w for w in ways.values() if w['nodes'][0] in retained]
    usage=Counter(n for w in chosen for n in set(w['nodes']))
    features=[]
    for way in sorted(chosen,key=lambda w:w['id']):
        start=0
        for i in range(1,len(way['nodes'])):
            if usage[way['nodes'][i]]>1 or i==len(way['nodes'])-1:
                portion=way['nodes'][start:i+1]
                coordinates=[nodes[n] for n in portion]
                if len({tuple(c) for c in coordinates})>1:
                    features.append({'type':'Feature','properties':{'id':f'OSM-{way["id"]}-{start}', 'upstream_node':f'osm:{portion[0]}','downstream_node':f'osm:{portion[-1]}','name':way.get('tags',{}).get('name:en') or way.get('tags',{}).get('name') or 'Periyar tributary', 'osm_way_id':way['id'], 'source':'OpenStreetMap','source_url':f'https://www.openstreetmap.org/way/{way["id"]}', 'mainstem':way['id'] in members,'demo':False},'geometry':{'type':'LineString','coordinates':coordinates}})
                start=i
    topology=nx.DiGraph()
    for f in features:
        p=f['properties'];topology.add_edge(p['upstream_node'],p['downstream_node'])
    source_digest=hashlib.sha256(json.dumps(features,sort_keys=True).encode()).hexdigest()[:12]
    collection={'type':'FeatureCollection','name':'Periyar mapped river network','version':'osm-'+source_digest,'features':features}
    (DATA/'river_network.geojson').write_text(json.dumps(collection,ensure_ascii=False),encoding='utf-8')
    coords=[c for f in features for c in f['geometry']['coordinates']]
    metadata={'mode':'osm','label':'OpenStreetMap river geometry; demonstration assets','version':collection['version'],'source':'© OpenStreetMap contributors','source_url':'https://www.openstreetmap.org/relation/11778217','license':'ODbL 1.0','retrieved_at':datetime.now(timezone.utc).isoformat(),'segment_count':len(features),'coordinate_count':len(coords),'way_count':len(chosen),'components':nx.number_weakly_connected_components(topology),'bounds':[min(c[0] for c in coords),min(c[1] for c in coords),max(c[0] for c in coords),max(c[1] for c in coords)],'limitations':['Community-mapped centerlines, not an official organizer or hydrological survey.','Only source-connected river ways within the documented extract and the complete Periyar relation are included. Minor streams not present in the extract are not invented.','Source gaps, reservoir discontinuities and tidal flow uncertainty are retained. Analysis stops at missing connections.','Flow follows OSM way order; no inferred flow reversal or artificial connecting segments.','Settlements, intakes, monitoring points and local-body polygons remain clearly labelled demonstration assets.']}
    lon,lat = min([c for f in features if f['properties']['mainstem'] for c in f['geometry']['coordinates']], key=lambda c:(c[0]-76.38)**2+(c[1]-10.12)**2)
    metadata['demo_location']={'latitude':lat,'longitude':lon}
    metadata['outlet_boundary']={'excluded_osm_way':613007375,'reason':'Edakochi Kayal belongs to the separate backwater network beyond the southern Periyar outlet. Excluding it prevents importing the Pamba, Manimala and Muvattupuzha basins.'}
    (DATA/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':main()
