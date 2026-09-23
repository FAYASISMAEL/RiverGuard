"""Place explicitly synthetic assets along the real mapped demo route.

Never changes river geometry; not a source of real infrastructure locations.
"""
import json
from pathlib import Path
from backend.app.river_impact_engine import RiverImpactEngine

ROOT=Path(__file__).resolve().parents[1]/'data'

def main():
    gis=RiverImpactEngine(ROOT)
    point=gis.metadata['demo_location']
    snap=gis.snap_engine.snap(**point)
    route=gis.flow_engine.traverse(snap['segment_id'],snap['offset_m'])
    def asset(identifier,name,distance,kind):
        choices=[p for p in route if p['distance']<=distance<=p['distance']+p['geometry'].length and p['geometry'].geom_type=='LineString']
        if not choices:raise ValueError(f'Demo path does not reach {distance} m')
        part=choices[0];location=part['geometry'].interpolate(distance-part['distance'])
        lon,lat=gis.inverse(location.x,location.y)
        return {'type':'Feature','properties':{'id':identifier,'name':name+' (sample)','local_body':'Demo local jurisdiction','demo':True,'segment_id':part['id']},'geometry':{'type':'Point','coordinates':[lon,lat]}}
    sets={'settlements':[asset('S-01','Downstream community A',1800,'settlements'),asset('S-02','Downstream community B',6000,'settlements')], 'water_intakes':[asset('W-04','Water intake W-04',750,'water_intakes')], 'monitoring_points':[asset('M-02','Monitoring point M-02',3000,'monitoring_points')]}
    for name,features in sets.items():(ROOT/f'{name}.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},indent=2),encoding='utf-8')
    print('Prepared synthetic assets on the sourced river network')

if __name__=='__main__':main()
