# Deploy the complete RiverGuard website on Vercel

One Vercel project serves the React frontend and FastAPI backend on the same domain. Reports, cases, sessions and evidence references live in PostgreSQL connected through Vercel Marketplace (Neon recommended). Photo bytes live in a **public Vercel Blob store**. No Render service is required.

## 1. Push the repository

Push the complete repository to GitHub, including root `vercel.json`, `requirements.txt`, `.python-version`, `api/server.py`, `backend`, `frontend` and the active `data/*.geojson` / `data/metadata.json` files. Keep `.env`, database files, uploaded photos, `.venv` and `node_modules` out of Git. Source-download caches are not needed in the deployment bundle.

## 2. Import the project in Vercel

- Choose the GitHub repository.
- **Root Directory: repository root (`.`). Do not select `frontend`.**
- Framework Preset: **Vite**.
- Install Command: `npm ci --prefix frontend`.
- Build Command: `npm run build --prefix frontend`.
- Output Directory: `frontend/dist`.

The checked-in `vercel.json` supplies these commands and routes `/api/*` and `/uploads/*` to the Python function before the SPA fallback. Direct links to `/admin`, `/history` and report details work. Python is pinned to 3.12. The runtime requirements omit development-only GeoPandas, pandas, pytest and GIS source-download tooling.

**Set `VITE_API_BASE_URL=/api` (or leave it unset). Remove any old `VITE_API_URL` setting.** Every request uses the centralized API client. The UI and backend share the same domain; never use localhost as the production API base.

## 3. Connect durable storage

In the Vercel project's **Storage** tab:

1. Connect/create **Neon Postgres** through Marketplace. Choose the environments to connect. Ensure `DATABASE_URL` contains the provider's **pooled PostgreSQL connection URL**, with its TLS parameters (normally `sslmode=require`). The application accepts `postgres://`, `postgresql://` and `postgresql+psycopg://` URLs.
2. Create/connect a **Vercel Blob store with Public access**. Confirm that the project receives `BLOB_READ_WRITE_TOKEN`. Photos are public evidence, matching the existing public galleries. This adapter does not support a private Blob store.
	The app accepts `DATABASE_URL`, `POSTGRES_URL`, `POSTGRES_PRISMA_URL`, or `NEON_DATABASE_URL` for the pooled Neon connection. These are common variables added by Neon/Vercel integrations. If Blob is not configured, uploads return a controlled 503 explanation. No photo is reported as saved to temporary storage. Map routes remain available.

Connect storage to Production and, if previews are needed, to Preview too. Prefer a separate database/store for previews so testing does not modify production reports. If Vercel needs an initial import/deployment before showing Storage, create the project, connect storage, then redeploy. Without PostgreSQL, map endpoints can still serve the bundled river data, but report saving and admin sessions return a controlled DATABASE_UNAVAILABLE error. Map loading and downstream analysis do not require a database; analysis explicitly reports when repeat-report history is unavailable.

## 4. Set environment variables

Set these under **Project → Settings → Environment Variables**. Keep their actual values in Vercel, never in source code:

```env
DATABASE_URL=postgresql://USER:PASSWORD@YOUR-POOLED-HOST/DATABASE?sslmode=require
BLOB_READ_WRITE_TOKEN=the-token-from-your-connected-public-blob-store
ADMIN_USERNAME=admin123
ADMIN_PASSWORD=your-admin-password
STORAGE_BACKEND=vercel_blob
COOKIE_SECURE=true
MAX_IMAGES_PER_REPORT=5
```

The existing hackathon password `admin@123` still works if you explicitly choose it; use a different value for a publicly accessible production site.

Do **not** copy the local SQLite `DATABASE_URL`, local `UPLOAD_DIR`, or Windows `DATA_DIR` into Vercel. Leave `DATA_DIR` unset so packaged river data is discovered relative to the Python module. Vercel supplies `VERCEL=1` automatically. This enables durable-storage checks, secure cookies, the cloud upload limit and exact deployment-domain allowlisting.

The app trusts exact domains supplied through `VERCEL_URL`, `VERCEL_PROJECT_PRODUCTION_URL` and `VERCEL_BRANCH_URL`; it does not trust every `*.vercel.app` site. Enable automatically exposed System Environment Variables in the Vercel project if disabled. For a custom domain, explicitly set:

```env
CORS_ORIGINS=https://riverguard.example.com,https://your-project.vercel.app
```

Use complete HTTPS origins, no `/admin` suffix. Redeploy after environment changes. This setting prevents the earlier “Untrusted request origin” failure without disabling origin/CSRF checks.

## 5. Deploy and check

Redeploy after connecting storage. On the first database-backed request, missing tables are created additively in PostgreSQL. Database initialization does not run during river startup. A database advisory lock prevents simultaneous cold instances from racing schema creation. Database connections are released after requests; use the provider's pooled endpoint.

Verify:

1. `/api/health` returns valid JSON. With all services configured it reports `status: ok`, `map: available`, `database: connected`, `storage: available`. Without optional services it reports `degraded`. Storage status checks configuration, not Blob credentials; confirm credentials with a real upload.
2. `/api/config` returns a 4 MiB per-image limit and maximum five photos.
3. `/map` loads the river.
4. `/admin` logs in with your configured credentials and survives refresh.
5. Submit a three-photo report; view its gallery and find it in History.
6. Review/verify/resolve it and confirm the timeline survives refresh.
7. Redeploy and confirm reports, sessions and photos remain available.

On Vercel, each photo is limited to **4 MiB** to leave multipart overhead below the platform's 4.5 MB function request limit. Each photo is sent separately, decoded and re-encoded to JPEG, then stored in Blob. Local development retains its previous 5 MiB limit. The UI reads the actual limit from `/api/config`. Larger uploads would require a direct-to-Blob upload flow, which is not implemented here.

## Local development and existing data

Existing local SQLite reports and the `uploads` directory remain untouched. With no `VERCEL=1` setting, the app defaults to the original local database and filesystem storage. Install dependencies with `python -m pip --python .venv/Scripts/python.exe install -r backend/requirements.txt`, then run the usual uvicorn and Vite commands.

A new hosted database starts empty. Deploying source code does **not** transfer existing local reports/photos. Do not upload the SQLite file to the serverless filesystem: it would not provide durable data. Data migration is a separate operation; retain a backup of the local database and photos if you need those records online.

## Troubleshooting

- **Health reports database unavailable or login returns DATABASE_UNAVAILABLE:** connect Neon and replace the copied local SQLite `DATABASE_URL`; redeploy.
- **Photo upload reports it could not store the photo:** confirm the Blob store is Public and its `BLOB_READ_WRITE_TOKEN` is connected to this deployment environment; inspect function logs.
- **Untrusted request origin:** add the exact domain to `CORS_ORIGINS`, enable Vercel System Environment Variables, and redeploy.
- **API routes return HTML:** confirm Root Directory is the repository root and root `vercel.json` is deployed. Remove any old frontend-only/external-backend rewrites.
- **Login succeeds then disappears:** remove `VITE_API_URL`; all API requests must use the current HTTPS site. Do not disable secure cookies.
- **Database connection fails:** use the provider's pooled URL with TLS, confirm credentials and environment scope, and redeploy.
- **No river data:** keep the five active GeoJSON files and metadata in the repository; leave `DATA_DIR` unset.

## Validation scope

Local tests cover existing workflows, cloud configuration guards, cloud evidence references across app restarts, storage failures and upload-size enforcement. Blob calls are mocked in automated tests. An actual Vercel build/deployment and live Neon/Blob round trip require a connected Vercel project and storage credentials; local test success does not substitute for the deployed checks above.

References: [Python API functions](https://vercel.com/docs/functions/runtimes/python/api-directory), [Vercel Blob server uploads](https://vercel.com/docs/vercel-blob/server-upload), [Marketplace storage](https://vercel.com/docs/marketplace-storage), [Function limits](https://vercel.com/docs/functions/limitations).


## Production-build simulation

The local preview helper serves the compiled React assets and real ASGI app on one origin. It is excluded from the Vercel function and is not a replacement for an actual Vercel build.

```powershell
npm run build --prefix frontend
.venv/Scripts/python.exe -m uvicorn scripts.preview_vercel:app --host 127.0.0.1 --port 4173
```

To simulate missing cloud services, start the helper with `VERCEL=1`, `PYTHON_DOTENV_DISABLED=1` and no database/Blob environment variables. In another terminal:

```powershell
cd frontend
$env:E2E_BASE_URL='http://127.0.0.1:4173'
$env:VERCEL_SIMULATION='1'
npx playwright test tests/deployment.spec.js
```

These checks cover desktop/mobile direct navigation and refresh, all river layers, database-independent analysis, controlled admin errors and recovery from a temporary map API failure. Normal workflows are separately covered by `journey.spec.js` with local persistence enabled.

The health endpoint intentionally returns 200 with a `degraded` status when optional services are absent; persistence-dependent operations return 503 rather than pretending a report or session was saved. Legacy local images remain accessible even if they predate the upload registry table.
