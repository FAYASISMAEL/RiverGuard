import json
from pathlib import Path
import pytest
from shapely.geometry import Point
from backend.app.river_impact_engine import RiverImpactEngine
from backend.app.river_impact_engine.snap_engine import ProximityError

DIRECTORY=Path(__file__).resolve().parents[1]/'data'

@pytest.fixture(scope='module')
def actual():return RiverImpactEngine(DIRECTORY)

def test_no_invented_coordinates_or_missing_mainstem(actual):
    elements=json.loads((DIRECTORY/'source/waterways.json').read_text(encoding='utf-8'))['elements']+json.loads((DIRECTORY/'source/periyar_relation.json').read_text(encoding='utf-8'))['elements']
    nodes={e['id']:[e['lon'],e['lat']] for e in elements if e['type']=='node'}
    source_coordinates={tuple(c) for c in nodes.values()}
    source_edges=set()
    for e in elements:
        if e['type']=='way':source_edges.update((tuple(nodes[a]),tuple(nodes[b])) for a,b in zip(e['nodes'],e['nodes'][1:]) if a in nodes and b in nodes)
    features=actual.datasets['river_network']['features']
    for feature in features:
        coords=feature['geometry']['coordinates']
        assert all(tuple(c) in source_coordinates for c in coords)
        assert all((tuple(a),tuple(b)) in source_edges for a,b in zip(coords,coords[1:]))
        assert feature['properties']['demo'] is False
    relation=next(e for e in elements if e['type']=='relation' and e['id']==11778217)
    assert {m['ref'] for m in relation['members'] if m['type']=='way'} <= {f['properties']['osm_way_id'] for f in features}
    assert 'Pamba' not in {f['properties']['name'] for f in features}

def test_real_upstream_middle_tributary_confluence_downstream_and_offsets(actual):
    fs=actual.datasets['river_network']['features'];main=[f for f in fs if f['properties']['mainstem']]
    upstream=min(main,key=lambda f:min(c[1] for c in f['geometry']['coordinates']))
    downstream=min(main,key=lambda f:min(c[0] for c in f['geometry']['coordinates']))
    tributary=next(f for f in fs if f['properties']['name']=='Muthirapuzha')
    middle=min(main,key=lambda f:min((c[0]-76.98)**2+(c[1]-9.94)**2 for c in f['geometry']['coordinates']))
    for feature in [upstream,middle,tributary,downstream]:
        coords=feature['geometry']['coordinates'];lon,lat=coords[len(coords)//2]
        result=actual.analyze(lat,lon)
        assert result['snapped_location']['snap_distance_m']<0.1
        assert result['downstream_segments']
        if feature is upstream:
            assert any(min(c[0] for c in part['geometry']['coordinates'])<76.18 for part in result['downstream_path']['features'] if part['geometry']['type']=='LineString')
    confluence=next(n for n in actual.flow_engine.graph if actual.flow_engine.graph.in_degree(n)>1)
    p=actual.snap_engine.lines[confluence].coords[0];lon,lat=actual.inverse(*p)
    assert actual.analyze(lat,lon)['snapped_location']['snap_distance_m']<0.1
    point=actual.metadata['demo_location'];near=actual.analyze(point['latitude']+0.0002,point['longitude'])
    assert 0<near['snapped_location']['snap_distance_m']<50
    with pytest.raises(ProximityError):actual.analyze(12,78)
