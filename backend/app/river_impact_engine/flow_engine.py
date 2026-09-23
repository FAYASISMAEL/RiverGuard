import networkx as nx
from shapely.ops import substring

class FlowEngine:
    def __init__(self, features, lines):
        self.lines = lines
        self.graph = nx.DiGraph()
        self.features = features
        starts = {}
        for feature in features:
            p = feature['properties']
            self.graph.add_node(p['id'])
            starts.setdefault(p['upstream_node'], []).append(p['id'])
        for feature in features:
            p = feature['properties']
            for next_id in starts.get(p['downstream_node'], []):
                self.graph.add_edge(p['id'], next_id, weight=lines[p['id']].length)

    def traverse(self, segment_id, offset):
        # Dijkstra visits each segment finitely, including malformed cyclic input.
        distances = nx.single_source_dijkstra_path_length(self.graph, segment_id)
        result = []
        for key, distance in sorted(distances.items(), key=lambda item: item[1]):
            start = offset if key == segment_id else 0
            result.append(dict(id=key, distance=max(0, distance-offset), start_offset=start, geometry=substring(self.lines[key], start, self.lines[key].length)))
        return result
