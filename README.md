# RiverGuard — Periyar River Watch

A citizen reporting and downstream-impact prototype built with React, Vite, Tailwind, React Leaflet, FastAPI, SQLAlchemy, Shapely, NetworkX and PyProj. GeoPandas validates the source datasets. Reports, evidence images, case IDs, timelines, priority snapshots, simulated alerts and admin actions persist in SQLite.

## Run locally

From `D:\MyWorks\RiverGuard`, start the backend:

```powershell
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd D:\MyWorks\RiverGuard\frontend
npm run dev
```

Open http://127.0.0.1:5173. Admin: http://127.0.0.1:5173/admin. API docs: http://127.0.0.1:8000/docs.

Hackathon login is case-sensitive: **admin123 / admin@123**. Configure `ADMIN_USERNAME` and `ADMIN_PASSWORD` in `.env`; restart the backend after changes. The public navigation has no Authority section. Admin sessions use database-backed opaque tokens in HttpOnly cookies, expire after eight hours by default, survive refresh and are revoked on logout. Mutations require the session and CSRF token. Use `COOKIE_SECURE=true` when deploying behind HTTPS.

First-time installation (Python 3.11+, Node 20.19+ or 22.12+):

```powershell
python -m venv .venv
python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt
# Only copy when .env does not already exist:
Copy-Item .env.example .env
cd frontend
npm ci
```

If Windows Store Python fails while bootstrapping pip, create the environment with `python -m venv --without-pip .venv`, then use the host-pip command above. Linux/macOS use `.venv/bin/python`.

## Demonstrate the complete workflow

1. Open Live Map. Zoom into the lower Periyar near **10.1200287, 76.379479**. Use layer controls to hide overlapping observations if needed. Click the river, select **Dead Fish**, then choose **Report Observation**.
2. Complete **Describe → Add Evidence → Select Location → Review → Submit**. Add three JPEG, PNG or WebP photos. Previews can be opened and removed. Default limit: five photos, 5 MB each; configure `MAX_IMAGES_PER_REPORT`.
3. Submit. The report receives a permanent ID, an unverified status, a snapped location, downstream analysis, priority and generated simulated alerts. This sample location has downstream demonstration assets and scores HIGH for a first report; repeated recent reports can raise it to CRITICAL.
4. Open History, search the report ID, and refresh to check persistence.
5. Visit `/admin`, log in, open the report, inspect all three photos, choose **Accept / Start Review**, then **Verify**. A permanent case ID links to the original report.
6. For verified HIGH/CRITICAL reports, use the Emergency action panel. Authority alerts, intake notifications, field inspections, monitoring notifications, community advisories and control actions save timeline events. Notifications are **simulated**, never sent externally.
7. Resolve the case. Refresh and inspect the public History page: images, status, case ID, alerts and timeline remain available.

The homepage **Load Demo Scenario** creates a labelled sample observation through the regular report service. To add labelled historical examples, run `.venv/Scripts/python.exe -m scripts.seed_history`. Seeds are idempotent. Browser tests also create clearly labelled sample records; they do not delete existing records.

## River provenance and limits

The active river is sourced from [OpenStreetMap Periyar relation 11778217](https://www.openstreetmap.org/relation/11778217) and source-connected river ways, retrieved 23 September 2026. Attribution: © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright).

The bundled extract contains **58 source ways, 62 graph segments and 5,474 coordinate entries**, including all 25 main-relation ways, connected tributaries and coastal branches. The importer preserves original WGS84 coordinates and way order, splits at shared nodes, and adds no artificial connectors or offsets. A separate southern backwater connection is excluded to avoid importing unrelated Pamba, Manimala and Muvattupuzha catchments. Source JSON and detailed metadata are under `data/source/` and `data/metadata.json`.

This is community-mapped geometry, not an official river survey. Minor streams absent from the extract are not invented. Flow follows source way order; reservoir gaps, missing connections and tidal uncertainty are not resolved by this prototype. Analysis stops at missing connections. **Intakes, communities, monitors and local-body boundaries are synthetic demonstration assets**, not verified infrastructure. All alerts are simulated. Priority describes potential network exposure, not confirmed contamination, concentration, travel time or health risk.

Old reports and their original snapshots remain intact. Archived routes from a different dataset version are not drawn on the current river. The schematic network is retained only in `tests/fixtures/demo`; `scripts/generate_data.py` regenerates those test fixtures, not the active map.

To reproduce the source import, run `python scripts/import_osm.py`, then `.venv/Scripts/python.exe -m scripts.prepare_demo_assets`. Restart the backend after dataset changes. `scripts/download_osm_connected.py` is the optional network-fetch preparation step. See [DATASET_SCHEMA.md](DATASET_SCHEMA.md) before replacing datasets.

## Routes and architecture

Public routes: `/`, `/map`, `/report`, `/history`, `/reports/:id`, `/hotspots`, `/about`. Legacy `/reports` and `/insights` links continue to work. `/authority` redirects to admin login.

Protected routes: `/admin/dashboard`, `/admin/reports`, `/admin/reports/:id`, `/admin/cases`. Admin lists support report/case/location/category/priority/date/segment/status searches and today's reports.

- `frontend/src/pages`: citizen workflow, history, maps, admin dashboard and case detail.
- `frontend/src/services`: credentialed HTTP client, CSRF and session state.
- `backend/app/auth.py`: login, persistent session, logout and authorization.
- `backend/app/admin.py`: dashboard, report/case lists, recorded response actions.
- `backend/app/services.py`: transactional report creation, snapshots, status transitions, timeline and alerts.
- `backend/app/river_impact_engine`: Snap → Flow → Impact → Priority.
- `backend/app/models.py`: existing Report/Alert tables plus additive CaseFile, ReportImage, AdminSession and AdminAction tables. Startup creates missing tables without resetting existing data. Legacy single-image references still work.

WGS84 display coordinates are projected into UTM 43N for metric analysis. Snapping uses a 500 m default proximity threshold. Weighted directed traversal clips the first segment at the snapped point, handles cycles and computes shortest downstream distances. Assets must be associated with traversed reaches and pass the 300 m lateral corridor threshold; upstream and disconnected assets are excluded. Polygon distance uses the first downstream intersection.

Priority conditions: intake +3, settlement +2, repeated non-rejected report on the segment in 30 days +2, intake/settlement within 1.5 km downstream +2, monitoring point +1. LOW 0–2, MEDIUM 3–6, HIGH 7–9, CRITICAL 10. Snapshots are not recalculated when later reports arrive.

Status transitions preserve existing behavior: UNVERIFIED → UNDER REVIEW / VERIFIED / REJECTED; UNDER REVIEW → VERIFIED / REJECTED; VERIFIED → RESOLVED. REJECTED and RESOLVED are terminal. Every change appends a timeline event. Alert states: Generated → Sent - Simulated → Acknowledged.

## API and errors

Explore `/docs` for full schemas. Core endpoints:

- `GET /api/config`, `/api/health`, `/api/map-metadata`, `/api/map/{layer}`.
- `POST /api/analyze`: latitude/longitude; snap, downstream path, assets and priority preview.
- `POST /api/uploads`: one multipart file; decoded, validated and re-encoded to strip metadata.
- `POST /api/reports`: report fields plus `image_urls`; legacy `image_url` remains accepted.
- `GET /api/reports`, `/api/reports/{id}`, `/api/reports/{id}/impact`, `/api/reports/{id}/alerts`, `/api/hotspots`.
- `POST /api/admin/login`, `GET /api/admin/session`, `POST /api/admin/logout`.
- Protected `GET /api/admin/dashboard`, `/api/admin/reports`, `/api/admin/cases`.
- Protected `POST /api/admin/reports/{id}/opened`, `/api/admin/reports/{id}/actions`.
- Protected `PATCH /api/reports/{id}/status`, `POST /api/reports/{id}/alerts`, `PATCH /api/alerts/{id}`.

Validation returns 422, oversized evidence 413, missing resources 404, unauthenticated access 401, invalid CSRF 403, invalid state transitions 409, and unavailable datasets/database 503. UI errors are readable; input remains available after failed submission. Public report responses exclude reporter identity/contact. Images are public evidence, so avoid sensitive material.

## Verification

```powershell
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe -m scripts.validate_dataset
cd frontend
npm run build
npx playwright install chromium
# Keep both servers running:
npm run test:e2e
```

Backend tests use isolated temporary database/uploads. Browser tests use the running local database and create labelled sample records. Run them against a local demo instance. They cover three-photo submission, image removal/lightbox, persistence, login/logout/wrong credentials, protected routes, review/reject/verify/resolve, case creation, emergency actions, alert acknowledgment, history filters, responsive pages, upload errors and near/far map clicks. Screenshots are saved in `frontend/test-results/`.

GeoPandas validates all five datasets as valid EPSG:4326 geometry. Source tests compare every rendered river coordinate/edge against the retained OSM source, retain the complete main relation, and exercise upstream, middle, tributary and coastal snapping/traversal.

## Deployment notes

Vite proxies `/api` and `/uploads` to port 8000 locally. For deployment, use a same-origin reverse proxy and SPA deep-link fallback; configure `VITE_API_URL` and `CORS_ORIGINS` if hosting separately. Basemap tiles require internet; local river overlays and analysis do not. Follow your tile provider's usage policy; `VITE_TILE_URL` can select another provider.

Before operational deployment, replace synthetic assets with verified data, validate hydrological directions, add institutional identity/roles, migrations, backups, upload quotas/retention, pagination and monitoring. SQLAlchemy permits a later PostgreSQL migration; GIS components can move behind PostGIS interfaces. Real notifications require a separate delivery adapter. No concentration or travel-time model is implemented.
