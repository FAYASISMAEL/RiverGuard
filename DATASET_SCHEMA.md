# Dataset contract

All files are GeoJSON `FeatureCollection` objects in longitude/latitude WGS84 (EPSG:4326). Coordinates are `[longitude, latitude]`, never reversed. Metric operations use EPSG:32643 for the Periyar region. Replace all five files as a consistent set and restart the backend. The application loads and validates datasets once at startup.

## `river_network.geojson`

Each feature must have a nonzero `LineString` geometry. Coordinates must run **upstream to downstream**. Required properties:

- `id`: unique string, e.g. `R-18`.
- `upstream_node`: string node identifier at the first coordinate.
- `downstream_node`: string node identifier at the last coordinate.
- `name`: display name (optional).
- `demo`: boolean provenance label for the supplied demonstration files.

Segments connect only when one segment's `downstream_node` equals another's `upstream_node`. Geometric proximity or line crossings do not imply connectivity. Node coordinates should agree across connected segments. Normalize node IDs to strings; split reaches at every confluence/distributary. Use different node IDs for disconnected lines even when they are close. Coastal endpoints have no outgoing link. Explicit organizer edge lists should be converted into this node contract during data preparation.

```json
{"type":"Feature","properties":{"id":"R-18","upstream_node":"A","downstream_node":"B","name":"Periyar reach","demo":true},"geometry":{"type":"LineString","coordinates":[[76.46,10.13],[76.415,10.125]]}}
```

## Point assets

`settlements.geojson`, `water_intakes.geojson`, and `monitoring_points.geojson` each contain `Point` features. Required properties: unique string `id`, string `name`, and string `local_body`. Optional `segment_id` explicitly associates the asset to its servicing reach; it must reference an existing river ID. Without this field, the nearest reach is associated once at startup. This association is checked against directed traversal before applying the lateral corridor threshold.

Use `segment_id` when nearby parallel reaches or braided channels would make nearest-geometry matching ambiguous. Assets beyond the corridor are excluded even if an explicit reach is specified. Geometry should represent the intake/river access/monitoring point, not a distant office or settlement centroid. Add future population/vulnerability properties without changing the existing contract.

## Administrative boundaries

`local_bodies.geojson` contains valid `Polygon` or `MultiPolygon` features with unique string `id` and string `name`. Polygon interiors must represent jurisdiction; no jurisdiction is inferred from names alone. Boundaries are returned when their geometry intersects the downstream path. The distance is the earliest path intersection, not centroid distance.

## Output contract

Every affected asset includes `id`, `name`, `type`, `distance_downstream` (metres along the shortest traversed route from the snapped point), `coordinates` (WGS84 representative point), `local_body`, and `estimated_arrival_time` (null until a validated velocity model exists).

The initial snapped segment is included in `downstream_segments` because its downstream remainder is part of exposure. `downstream_path` clips that first segment to the snapped location. At the exact endpoint, its remaining geometry may be a Point. Snap metadata includes an internal `offset_m` along the complete reach. Priority scores are stored at submission time.

## Test fixture provenance

The schematic R-18?R-25 network, tributary T-01 and disconnected D-01 are retained only in `tests/fixtures/demo` for deterministic engine tests. They are not the active application river.

## Active source provenance and versioning

The active river dataset is now sourced from OpenStreetMap, not generated demonstration lines. It contains the complete Periyar relation 11778217 and connected river ways. `data/metadata.json` records retrieval time, source, ODbL attribution, coverage limitations, outlet exclusion and demo coordinates. The FeatureCollection `version` matches the metadata version and each saved impact snapshot. When a supplied collection omits a version, the engine derives a deterministic content hash and exposes it on the map collection and metadata response.

`data/source/periyar_relation.json` and `data/source/waterways.json` retain the original coordinates and node IDs. `scripts/import_osm.py` splits ways at shared source nodes and never creates artificial connecting edges or reverses way direction. OSM direction is not a validated tidal/reservoir hydrology model. Missing minor waterways are explicitly outside extract coverage.

All point assets and administrative polygons remain synthetic. `scripts/prepare_demo_assets.py` positions sample point assets along the sourced lower-river route without modifying the river. `scripts/generate_data.py` writes schematic fixtures only under `tests/fixtures/demo`.

For replacement data, preserve coordinate order and directed topology; supply a new collection version and matching metadata describing provenance. Old report snapshots must remain unchanged. The frontend deliberately suppresses archived downstream overlays when their dataset version differs from the active collection. Validate replacement files with `.venv/Scripts/python.exe -m scripts.validate_dataset` and restart the backend.
