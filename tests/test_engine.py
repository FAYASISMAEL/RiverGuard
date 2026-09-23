import pytest
from backend.app.config import DATA_DIR
from backend.app.river_impact_engine import RiverImpactEngine
from backend.app.river_impact_engine.snap_engine import ProximityError

@pytest.fixture(scope='module')
def gis():
    return RiverImpactEngine(DATA_DIR)

def test_directly_on_river(gis):
    result = gis.analyze(10.125, 76.415)
    assert result['snapped_location']['snap_distance_m'] < 1
    assert 'R-25' in result['downstream_segments']

def test_slightly_away(gis):
    assert 0 < gis.analyze(10.126,76.418)['snapped_location']['snap_distance_m'] < 500

def test_too_far(gis):
    with pytest.raises(ProximityError):
        gis.analyze(11,77)

def test_tributary(gis):
    route = gis.analyze(10.15,76.3917)['downstream_segments']
    assert route[0] == 'T-01'
    assert 'R-20' in route
    assert 'R-19' not in route

def test_before_confluence_never_enters_tributary(gis):
    route = gis.analyze(10.126,76.425)['downstream_segments']
    assert 'R-20' in route
    assert 'T-01' not in route

def test_multiple_settlements_and_nearby_intake(gis):
    result = gis.analyze(10.1253,76.418)
    assert len(result['affected']['settlements']) == 2
    assert result['affected']['water_intakes'][0]['id'] == 'W-04'
    assert result['affected']['water_intakes'][0]['distance_downstream'] < 1500
    assert result['priority']['level'] == 'HIGH'

def test_upstream_asset_on_same_segment_excluded(gis):
    assert gis.analyze(10.121,76.401)['affected']['water_intakes'] == []

def test_endpoint(gis):
    result = gis.analyze(10.18,76.20)
    assert result['downstream_segments'] == ['R-25']
    assert not result['affected']['settlements']

def test_disconnected(gis):
    assert gis.analyze(10.188,76.443)['downstream_segments'] == ['D-01']

def test_cycles_terminate(gis):
    graph = gis.flow_engine.graph
    graph.add_edge('R-25','R-18',weight=100)
    try:
        route=gis.analyze(10.1253,76.418)['downstream_segments']
        assert len(route) == len(set(route)) == 8
    finally:
        graph.remove_edge('R-25','R-18')

def test_missing_data(tmp_path):
    with pytest.raises(FileNotFoundError):
        RiverImpactEngine(tmp_path)

def test_asset_on_unconnected_nearby_branch_excluded(gis):
    from shapely.geometry import LineString
    from backend.app.river_impact_engine.impact_engine import ImpactEngine
    from backend.app.river_impact_engine.flow_engine import FlowEngine
    lines={'A':LineString([(0,0),(100,0)]), 'B':LineString([(0,50),(100,50)])}
    assets={'settlements':{'features':[{'properties':{'id':'s','name':'Other bank branch','local_body':'Test'},'geometry':{'type':'Point','coordinates':[60,50]}}]},'water_intakes':{'features':[]},'monitoring_points':{'features':[]},'local_bodies':{'features':[]}}
    matcher=ImpactEngine(assets,lambda x,y:(x,y),300,lines)
    assert not matcher.match([{'id':'A','distance':0,'start_offset':0,'geometry':lines['A']}])['settlements']

def test_boundary_distance_is_first_intersection():
    from shapely.geometry import LineString
    from backend.app.river_impact_engine.impact_engine import ImpactEngine
    line=LineString([(0,0),(100,0)])
    dataset={'local_bodies':{'features':[{'properties':{'id':'L','name':'Test'},'geometry':{'type':'Polygon','coordinates':[[[20,-10],[80,-10],[80,10],[20,10],[20,-10]]]}}]}}
    matcher=ImpactEngine(dataset,lambda x,y:(x,y),300,{'A':line})
    result=matcher.match([{'id':'A','distance':10,'start_offset':0,'geometry':line}])
    assert result['local_bodies'][0]['distance_downstream']==30
