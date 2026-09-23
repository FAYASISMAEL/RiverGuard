from shapely.geometry import shape, Point
from shapely import get_coordinates
from shapely.ops import transform

class ImpactEngine:
    def __init__(self, datasets, project, corridor, lines):
        self.corridor = corridor
        self.lines = lines
        self.assets = {key: [(f, transform(project, shape(f['geometry']))) for f in data['features']] for key, data in datasets.items()}
        # Associate point assets with one reach up front. A nearby parallel or
        # upstream tributary must not be included through a spatial buffer alone.
        self.associations = {}
        for kind, assets in self.assets.items():
            if kind != 'local_bodies':
                for feature, geometry in assets:
                    explicit = feature['properties'].get('segment_id')
                    segment = explicit or min(lines, key=lambda key: lines[key].distance(geometry))
                    if segment not in lines:
                        raise ValueError(f'Unknown asset segment: {segment}')
                    self.associations[(kind, feature['properties']['id'])] = segment

    def match(self, route):
        affected = {}
        for kind, assets in self.assets.items():
            affected[kind] = []
            for feature, geometry in assets:
                candidates = []
                for part in route:
                    line = part['geometry']
                    if kind == 'local_bodies':
                        intersection = line.intersection(geometry)
                        if not intersection.is_empty:
                            offset = min(line.project(Point(x,y)) for x,y in get_coordinates(intersection)) if line.geom_type == 'LineString' else 0
                            candidates.append(part['distance'] + offset)
                    elif self.associations[(kind, feature['properties']['id'])] == part['id']:
                        full = self.lines[part['id']]
                        offset = full.project(geometry)
                        if offset + 0.001 >= part['start_offset'] and full.distance(geometry) <= self.corridor:
                            candidates.append(part['distance'] + max(0, offset-part['start_offset']))
                if candidates:
                    p = feature['properties']
                    center = shape(feature['geometry']).representative_point()
                    affected[kind].append(dict(id=p['id'], name=p['name'], type=kind, distance_downstream=round(min(candidates)), coordinates=[center.x, center.y], local_body=p.get('local_body', p['name']), estimated_arrival_time=None))
            affected[kind].sort(key=lambda a: a['distance_downstream'])
        return affected
