# RiverGuard · Periyar River Watch

A working citizen observation and downstream-impact prototype for the Periyar river contamination challenge. React, Vite, Tailwind, React Leaflet, FastAPI, SQLAlchemy, Shapely, PyProj, and NetworkX power the complete workflow. SQLite persists reports, analyses, alert states, and verification history.

## Why this exists

A report is more than a pin. An upstream observation may affect water intakes and communities farther down the river. RiverGuard snaps a reported location to a directed reach, follows connected downstream reaches, and explains which mapped assets may be exposed. Authorities independently review whether an observation is verified.

**All bundled geography is illustrative demo data.** It resembles a lower-Periyar corridor but is not a surveyed river alignment, authoritative boundary dataset, or operational warning system. Alerts are simulated. Citizen observations are unverified by default. Priority and reporting frequency never confirm pollution.

## Run locally

Prerequisites: Python 3.11+ and Node.js 20.19+ (or 22.12+). Run backend commands from the repository root.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

If the Windows Store Python environment cannot bootstrap pip, use the already installed host pip:

```powershell
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. API documentation: **http://127.0.0.1:8000/docs**. Linux/macOS use `.venv/bin/python` in place of `.venv/Scripts/python.exe` and `cp .env.example .env`.

The five GeoJSON files are checked in. To regenerate them, run `python scripts/generate_data.py`. Missing or malformed datasets put GIS endpoints into a controlled HTTP 503 state; `/api/health` reports `degraded` and explains dataset availability. Correct the files and restart the backend.

To populate a fresh database with three sample observations and their alerts, run `.venv/Scripts/python.exe -m scripts.seed_demo` from the root. It is safe to repeat; identical seeded examples are not duplicated.

### Frontend commands

```sh
npm run dev       # local UI, proxies /api and /uploads to localhost:8000
npm run build     # production assets in frontend/dist
npm run preview   # preview static build (configure API URL or reverse proxy first)
```

For a separately hosted UI, set `VITE_API_URL` to the backend origin at build time and configure `CORS_ORIGINS`. A same-origin reverse proxy should route `/api` and `/uploads` to FastAPI and other paths to the SPA, falling back to `index.html` for deep links.

## Walk through the demo

1. On Overview, choose **Load Demo Scenario**. It creates a real persistent unverified report through the same service as citizen submissions.
2. The report near R-18 is snapped to the river; the highlighted path follows R-18 through R-25 without entering the tributary backwards.
3. Inspect two settlements, W-04 water intake, a monitoring station, and two local bodies. A first report scores **8 / HIGH**; repeated recent observations add 2 points.
4. Open the full report to inspect generated alert messages and the timestamped timeline.
5. Go to **Authority**, open the report, mark it under review, verify it, send a simulated alert, acknowledge it, and resolve the report.
6. Open **Insights** to see reporting frequency, categories, recent activity, and frequently affected reaches.

For the real input workflow, use **Report an observation**: Describe → Locate → Review & submit. Add an optional JPEG/PNG/WebP image; click a point near the blue river (around longitude 76.418, latitude 10.1253 for the upstream example). GPS can be used if the browser supports it and the device is actually near this demo corridor. Faraway locations are rejected rather than silently snapped.

## Architecture

```text
Citizen / Authority
       ↓
React pages → replaceable RiverMap component (React Leaflet)
       ↓
FastAPI routes → validated Pydantic input → report service
       ↓
river_impact_engine
   SnapEngine → FlowEngine → ImpactEngine → PriorityEngine
       ↓
SQLAlchemy models / SQLite + immutable startup-loaded GeoJSON
       ↓
Persisted impact + targeted simulated alerts + authority timeline
```

Repository layout:

- `frontend/src/pages/`: overview, live map, 3-step report form, report details, insights, authority dashboard.
- `frontend/src/map/`: the map adapter. Page-level state is plain data; replace the component for Google Maps or MapLibre without rewriting the engine.
- `frontend/src/services/`: HTTP client, error normalization, optional authority-key header.
- `backend/app/main.py`: routes, lifecycle, middleware, upload validation, authority dependency.
- `backend/app/services.py`: report transactions, repeat detection, alert generation, public serialization.
- `backend/app/river_impact_engine/`: four distinct GIS components plus startup orchestration.
- `backend/app/models.py`, `database.py`, `schemas.py`: persistence and validation boundaries.
- `data/`: replaceable GeoJSON assets, documented in [DATASET_SCHEMA.md](DATASET_SCHEMA.md).
- `tests/`: engine and API integration tests. `frontend/tests/`: real browser journeys.

### Downstream correctness

WGS84 inputs are projected into UTM 43N (EPSG:32643) before measuring distances. The nearest valid segment is selected and the submitted point is projected onto that line. `RIVER_PROXIMITY_M` defaults to 500 m.

The directed graph is built **once at backend startup** from downstream-node → upstream-node equality. Weighted traversal visits downstream-reachable segments only; a visited-distance map makes cycles finite. Missing links terminate that path safely. It supports tributaries, confluences, and distributaries. The starting segment is clipped at the snapped location. Distances account for that partial starting reach and take the shortest directed path at reconnections.

Point assets are associated with their explicit `segment_id`, or the nearest river segment during startup. They must belong to a traversed reach, lie downstream of the observation on that reach, and be within `ASSET_CORRIDOR_M` (300 m default). This prevents simple circular-buffer matches to an upstream or nearby disconnected branch. Local-body polygons must intersect the downstream path; reported distance is the first intersection along a traversed path. Local bodies can overlap and be returned independently.

Priority is a fixed, explainable snapshot at submission: intake +3; settlement +2; an existing non-rejected report on the same reach within 30 days +2; settlement/intake within 1.5 km downstream +2; monitor +1. Points are awarded once per condition, not per asset. LOW 0–2, MEDIUM 3–6, HIGH 7–9, CRITICAL 10. Existing analyses do not silently change when later reports arrive. Hotspot activity counts include rejected reports and are labelled as frequency, not confirmed contamination.

### Persistence and state

Every submission, impact, and alert batch is committed in one transaction. Public endpoints omit reporter identity/contact. Uploads are decoded, size/dimension checked, re-encoded as JPEG with metadata removed, and stored under generated filenames. Optional uploads that are not subsequently attached may remain until a future retention job is added.

Observation transitions: UNVERIFIED → UNDER REVIEW / VERIFIED / REJECTED; UNDER REVIEW → VERIFIED / REJECTED; VERIFIED → RESOLVED. REJECTED and RESOLVED are terminal. Invalid transitions return 409. Alert transitions: Generated → Sent - Simulated → Acknowledged. Alert generation is idempotent for an existing batch; messages retain the observation status at generation, while the report displays current verification status.

Without `AUTHORITY_API_KEY`, the application visibly operates in demo authority mode. Set a key and enter it in Authority access settings to restrict mutation endpoints. This is a prototype gate, not production identity management or per-authority attribution. Do not publicly deploy the unrestricted demo as an operational incident system.

## API

Interactive request/response schemas are available at `/docs` and `/openapi.json`.

- `POST /api/reports`: validate and persist a report, impact, timeline, and generated alerts (201).
- `GET /api/reports`, `GET /api/reports/{id}`: list / inspect observations.
- `POST /api/uploads`: multipart `file`; JPEG, PNG, WebP; maximum 5 MB / 20 megapixels (201).
- `POST /api/analyze`: `{ "latitude": 10.1253, "longitude": 76.418 }`; preview snap, route, assets, priority without persistence.
- `GET /api/reports/{id}/impact`: persisted analysis with current report status.
- `PATCH /api/reports/{id}/status`: `{ "status": "VERIFIED", "note": "Field review completed" }`; authority gate.
- `GET /api/hotspots`: total and last-30-day counts per reported segment; LOW / MODERATE / HIGH FREQUENCY at 1 / 2 / 5 recent observations.
- `GET /api/map/{layer}`: `river`, `settlements`, `intakes`, `monitoring-points`, `local-bodies`.
- `POST /api/reports/{id}/alerts`: generate batch if missing; authority gate.
- `GET /api/reports/{id}/alerts`: alert history and current delivery states.
- `PATCH /api/alerts/{id}`: `{ "state": "Sent - Simulated" }` or `Acknowledged`; authority gate.
- `POST /api/demo`: persist the built-in example using the standard report service (201).
- `GET /api/health`: dataset readiness and authority mode.

Validation errors use 422, missing resources 404, oversized images 413, denied authority actions 403, invalid transitions 409, unavailable GIS data 503. The UI shows loading/empty/error states and retains form input on submission failure.

## Tests

```powershell
.venv/Scripts/python.exe -m pytest tests -q
cd frontend
npx playwright install chromium
# Start both backend and frontend in other terminals first.
npm run test:e2e
```

Backend tests use a temporary database and upload directory. Browser tests intentionally create sample reports in the running local database; run them against a disposable local instance. They exercise a map click, image upload, submission, impact display, simulated alert delivery and acknowledgment, authority review/verification/resolution, demo loading, and mobile layouts. Screenshots are written to `frontend/test-results/`.

Engine cases cover an on-river report, nearby point, rejected distant location, tributary, pre-confluence location, multiple settlements, immediate intake, endpoint, disconnected segment, upstream exclusion, and finite cyclic traversal. API tests cover repeat scoring, hotspot counts, missing data, invalid images, unauthorized status changes, and timeline persistence.

## Production upgrade path

Set `DATABASE_URL` for PostgreSQL after installing the matching driver; SQLAlchemy models isolate the storage interface. Add Alembic migrations before evolving a deployed schema. Introduce PostGIS geometry columns and indexed spatial queries behind the GIS/repository interfaces when replacing in-memory datasets. Install GeoPandas in the data preparation pipeline if organizer data needs reprojection or format conversion; runtime GeoJSON operations use Shapely and PyProj directly.

Before operational deployment add identity/OIDC, role-based authority permissions, attributed immutable audit logs, rate limiting, paginated public feeds, upload quotas/retention and malware scanning, object storage, backup/restore, request monitoring, dataset version IDs, and calibrated organizer hydrology. Real SMS/email/push should use a queue and replace the simulated delivery adapter, with consent and delivery receipts. Add sensor ingestion as a separate service.

`estimated_arrival_time` is present but null. A future velocity model can estimate travel time from directed distance / flow velocity, with uncertainty and explicit **Estimated Travel Time** labelling. Current results make no claim about concentration, dispersion, tidal reversal, actual arrival times, or risk to human health. Network topology alone cannot provide those conclusions.

Base-map tiles need internet access; river/asset overlays and core analysis remain local. The default OpenStreetMap tile layer includes attribution and relies on normal browser caching; follow the [OSMF tile usage policy](https://operations.osmfoundation.org/policies/tiles/) and configure a suitable provider through `VITE_TILE_URL` before higher-volume deployment. Change attribution with your provider. The prototype uses in-memory graph traversal and linear nearest-reach lookup, suitable for the small demo; introduce STRtree/PostGIS indexes and bounded API pagination for large datasets. Tests and standard build commands are ready to be added to CI; Docker and cloud deployment can be layered on without changing the core engine.
