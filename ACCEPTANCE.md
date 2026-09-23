# Acceptance verification — 24 September 2026

- Backend: 21 tests passed (one upstream TestClient deprecation warning).
- Browser: 4 Playwright journeys passed against running frontend/backend.
- Frontend production build passed.
- Pyright: 0 errors, 0 warnings.
- GeoPandas: all five datasets valid EPSG:4326; 62 directed river segments and 62 links.

The browser workflow submitted three photos, removed/re-added a preview, opened the lightbox, refreshed, found the report in history, signed into admin, started review, verified, ran all six simulated response actions, acknowledged an alert, resolved, refreshed and confirmed the public status. Separate journeys checked wrong credentials, protected routes, logout, rejection, filters, empty/network-error states, evidence validation, responsive navigation and near/far snapping.

Reviewed screenshots: desktop home, mobile home, populated admin dashboard, upstream/middle/coastal river alignment. Further screenshots include tributary/confluence/near-river selection and the admin case. Generated screenshots are under `frontend/test-results/` (ignored by Git).

Browser journeys create labelled sample records in the local database. Existing records are preserved. Old dataset snapshots remain archived; their routes are suppressed on newer map versions.

Source geometry is community OpenStreetMap data, not an official hydrological survey. Missing minor waterways and tidal direction uncertainty remain documented in data/metadata.json. Impact assets are synthetic, and no external notifications are sent.
