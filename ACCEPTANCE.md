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

## Vercel adaptation verification

- 40 backend tests passed, including Blob storage mocks, stable evidence references after restart, cloud configuration validation, upload limits, startup without ASGI lifespan events, and missing database/Blob services.
- All 4 browser workflows and 3 API-error browser checks passed against the compiled SPA and real API with local persistence.
- Another 3 browser checks passed against the compiled SPA with `VERCEL=1` and database/Blob credentials absent: desktop/mobile direct navigation and refresh, river layers and analysis, controlled persistence errors, and recovery after one failed map request.
- Frontend production build passed; Python type checking returned zero errors/warnings.
- Static import capitalization and bundled GeoJSON checks passed. The five active GeoJSON files total 163,670 bytes. This does not measure the final dependency bundle or substitute for a Linux runtime test.
- Local reports and photos remain preserved.
- The initial development-server browser run failed because its esbuild worker had stopped. Vite was restarted; the full regression suite then passed against the compiled site.
- An actual `vercel build --yes` was attempted but stopped before building: the CLI reported an invalid login token. An authenticated Vercel build, Linux runtime, deployed file inclusion/bundle size, live Neon connectivity, and real Blob uploads remain unverified. Run `npx vercel login`, then follow VERCEL_DEPLOYMENT.md to link, build, deploy, and perform the live checks.
- Earlier live requests returned `FUNCTION_INVOCATION_FAILED`. The final live recheck of `/api/health` and `/api/map/river` at `river-guard-69sb.vercel.app` instead returned HTTP 404 `DEPLOYMENT_NOT_FOUND`. The Python runtime traceback has not been available, so the original deployed failure is not yet confirmed or verified fixed; the current project/deployment must also be located.
