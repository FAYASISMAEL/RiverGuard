"""Deterministic illustrative lower-Periyar network, never survey data."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'data'
ROOT.mkdir(exist_ok=True)

def feature(props, geometry):
    return {'type': 'Feature', 'properties': {**props, 'demo': True}, 'geometry': geometry}

def save(name, features):
    (ROOT / f'{name}.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, indent=2))

nodes = {'A': [76.46,10.13], 'B': [76.415,10.125], 'C': [76.38,10.115], 'D': [76.35,10.108], 'E': [76.325,10.11], 'F': [76.295,10.125], 'G': [76.265,10.145], 'H': [76.235,10.165], 'SEA': [76.20,10.18], 'T': [76.395,10.16], 'X': [76.45,10.19], 'Y': [76.43,10.185]}
links = [('R-18','A','B'),('R-19','B','C'),('R-20','C','D'),('R-21','D','E'),('R-22','E','F'),('R-23','F','G'),('R-24','G','H'),('R-25','H','SEA'),('T-01','T','C'),('D-01','X','Y')]
save('river_network', [feature({'id':i,'upstream_node':a,'downstream_node':b,'name':'Illustrative Periyar' if i.startswith('R') else 'Demo tributary / isolated reach'}, {'type':'LineString','coordinates':[nodes[a],nodes[b]]}) for i,a,b in links])
for name, rows in {
    'settlements': [('S-01','Aluva community',76.353,10.109,'Aluva Municipality'),('S-02','Kadungalloor community',76.30,10.123,'Kadungalloor Panchayat')],
    'water_intakes': [('W-04','Aluva water intake',76.408,10.123,'Aluva Municipality')],
    'monitoring_points': [('M-02','Lower Periyar monitoring point',76.28,10.135,'Kadungalloor Panchayat')],
}.items():
    save(name, [feature({'id':i,'name':label,'local_body':body}, {'type':'Point','coordinates':[lon,lat]}) for i,label,lon,lat,body in rows])
save('local_bodies', [feature({'id':i,'name':name}, {'type':'Polygon','coordinates':[[[west,10.08],[east,10.08],[east,10.17],[west,10.17],[west,10.08]]]}) for i,name,west,east in [('L-01','Aluva Municipality',76.32,76.42),('L-02','Kadungalloor Panchayat',76.24,76.32)]])


