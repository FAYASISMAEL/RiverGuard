import json
import hashlib
from pathlib import Path
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform
from .snap_engine import SnapEngine
from .flow_engine import FlowEngine
from .impact_engine import ImpactEngine
from .priority_engine import calculate_priority

class RiverImpactEngine:
    def __init__(self, directory: Path, threshold: float = 500.0, corridor: float = 300.0):
        names = ['river_network', 'settlements', 'water_intakes', 'monitoring_points', 'local_bodies']
        self.datasets = {name: json.loads((directory / f'{name}.geojson').read_text(encoding='utf-8')) for name in names}
        metadata_path = directory / 'metadata.json'
        self.metadata = json.loads(metadata_path.read_text(encoding='utf-8')) if metadata_path.exists() else {'mode':'supplied', 'label':'Supplied river network'}
        network = self.datasets['river_network']
        version = network.get('version') or 'network-' + hashlib.sha256(json.dumps(network, sort_keys=True).encode()).hexdigest()[:12]
        self.metadata['version'] = version
        self.metadata.setdefault('label', 'Supplied river network')
        network['version'] = version
        for name, dataset in self.datasets.items():
            if dataset.get('type') != 'FeatureCollection' or not isinstance(dataset.get('features'), list):
                raise ValueError(f'{name} must be a GeoJSON FeatureCollection')
            seen = set()
            for feature in dataset['features']:
                p = feature['properties']
                identifier = p['id']
                if not isinstance(identifier, str) or not identifier or identifier in seen:
                    raise ValueError(f'{name}: IDs must be unique nonempty strings')
                seen.add(identifier)
                geometry = shape(feature['geometry'])
                allowed = ['LineString'] if name == 'river_network' else ['Polygon','MultiPolygon'] if name == 'local_bodies' else ['Point']
                if geometry.geom_type not in allowed or geometry.is_empty or not geometry.is_valid:
                    raise ValueError(f'{name}: invalid geometry for {identifier}')
                west, south, east, north = geometry.bounds
                if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
                    raise ValueError(f'{name}: coordinates must be WGS84 longitude/latitude')
                required = ['upstream_node','downstream_node'] if name == 'river_network' else ['name'] if name == 'local_bodies' else ['name','local_body']
                if any(not isinstance(p.get(key), str) or not p[key] for key in required):
                    raise ValueError(f'{name}: required string properties missing for {identifier}')
        project = Transformer.from_crs('EPSG:4326', 'EPSG:32643', always_xy=True).transform
        self.inverse = Transformer.from_crs('EPSG:32643', 'EPSG:4326', always_xy=True).transform
        features = self.datasets['river_network']['features']
        self.properties = {f['properties']['id']: f['properties'] for f in features}
        if not features:
            raise ValueError('River dataset is empty')
        ids = [f['properties']['id'] for f in features]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate river segment IDs')
        lines = {f['properties']['id']: transform(project, shape(f['geometry'])) for f in features}
        if any(line.geom_type != 'LineString' or line.length == 0 for line in lines.values()):
            raise ValueError('River segments must be nonempty LineStrings')
        self.snap_engine = SnapEngine(lines, project, self.inverse, threshold)
        self.flow_engine = FlowEngine(features, lines)
        self.impact_engine = ImpactEngine({k: v for k, v in self.datasets.items() if k != 'river_network'}, project, corridor, lines)

    def analyze(self, latitude, longitude, repeat_count=0):
        snap = self.snap_engine.snap(latitude, longitude)
        snap['name'] = self.properties[snap['segment_id']].get('name', 'Periyar River')
        route = self.flow_engine.traverse(snap['segment_id'], snap['offset_m'])
        affected = self.impact_engine.match(route)
        return dict(snapped_location=snap, downstream_segments=[part['id'] for part in route], affected=affected,
                    downstream_path={'type': 'FeatureCollection', 'features': [{'type': 'Feature', 'properties': {'id': part['id']}, 'geometry': mapping(transform(self.inverse, part['geometry']))} for part in route]},
                    priority=calculate_priority(affected, repeat_count), dataset_mode=self.metadata['label'], dataset_version=self.metadata['version'])
