# kjnsfivjnfrikvnjf

A focused January 2026 wind-forecast pilot: reconstruct the forecast available at a day-ahead decision cutoff, then evaluate it against actual generation. React/TypeScript frontend, Python/FastAPI backend, and Docker packaging.

**Status:** local implementation. Public deployment, anonymous public repository publication, YouTube demo, and submission remain pending. There is no public deployment URL yet.

## Run

With Docker installed and running:

```sh
docker compose up --build
```

Open http://localhost:8000. The bundled real Elexon snapshot means no API credentials or live ingestion are required to run the app.

Without Docker (Python 3.9+ and Node 22.12+):

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.lock.txt
cd frontend
npm ci
npm run build
cd ..
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

For frontend hot reload, run `npm run dev` in `frontend/` with the backend on port 8000; Vite proxies `/api` to it. The production build is served directly by FastAPI, using the same origin as the API.

## What is included

| Path | Purpose |
| --- | --- |
| `frontend/src/App.tsx` | Decision, retrospective accuracy, and methodology views |
| `frontend/src/Charts.tsx` | Profile, daily MAE, and signed-error charts |
| `frontend/src/api.ts` | Cancellable API requests, formatting, and error state |
| `frontend/src/types.ts` | Response types |
| `frontend/src/styles.css` | Responsive interface |
| `backend/main.py` | API validation and production static serving |
| `backend/domain.py` | Pure forecast selection and metric calculations |
| `backend/ingest.py` | Repeatable two-endpoint ingestion and validation |
| `backend/tests/` | Domain and API tests |
| `data/snapshot.json` | Versioned real pilot data |
| `data/raw/` | Compressed original Elexon responses |
| `data/manifest.json` | Request URLs, retrieval timestamps, response hashes |
| `Dockerfile`, `compose.yaml` | Multi-stage build and local container runtime |
| `heroku.yml` | Heroku container build definition |

## Data and methodology

Only the specified APIs supply product data:

- [FUELHH/stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream): `fuelType=WIND`; actual MW by `startTime`.
- [WINDFOR/stream documentation](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream): forecast MW by `startTime` and `publishTime`.

The corresponding API base is `https://data.elexon.co.uk/bmrs/api/v1/datasets`. Full request URLs are retained in the manifest.

Decision dates are January 1–31, 2026; delivery dates are January 2–February 1. The configurable default cutoff, 10:00 Europe/London, is a pilot convention and **not an asserted auction deadline**. All January times are GMT. Internally timestamps are normalized to UTC.

For each delivery timestamp, select the latest forecast whose publication time is no later than the decision cutoff. Later vintages never fill missing values. The UI retains publication timestamps and identifies mixed-vintage profiles. Actuals are hidden by default and explicitly labelled as hindsight when revealed.

### Important: the sources have different resolutions

The actual API responses contain hourly WINDFOR timestamps and half-hourly FUELHH values. [Elexon's wind-generation page](https://bmrs.elexon.co.uk/wind-generation) confirms the hourly forecast resolution. The application uses **exact timestamp matching**, with no interpolation, forward filling, or alternative data source.

At 10:00, this snapshot has 744 matched timestamps out of 1,488 half-hourly delivery slots. The other 744 are intentionally unmatched, not a download failure. Metrics describe the exact-match subset. Partial energy values cover matched half-hour slots only and must not be extrapolated to full-day or client procurement quantities.

Define error = forecast − actual. Positive means wind was overforecast.

- MAE: mean absolute error, MW.
- RMSE: square root of mean squared error, MW.
- Bias: mean signed error, MW.
- Overforecast frequency: positive errors / matched intervals.
- Shortfall energy: sum(max(error, 0) × 0.5 hours), MWh, **partial**.

Monthly metrics are calculated from individual matched pairs, not unweighted daily averages. Missing values are never zero. Zero generation is valid. No pairs means unavailable metrics. MAPE and predictive confidence intervals are not used.

### Data quality and revisions

Raw records are normalized and exact duplicates removed. Invalid non-numeric, non-finite, negative, or misaligned records are excluded and counted. Conflicting values at the latest eligible publication make that timestamp unavailable; an older version is not silently substituted. Actuals use the latest retrieved publication per startTime and may include revisions. This does not reconstruct actuals as known in January.

Publication time is an availability proxy, not proof of receipt by a trader. Coverage is Elexon-reported national wind, not every wind installation in the UK. Wind alone cannot determine a utility's purchases without demand and contracted supply.

## Refresh data

```sh
source .venv/bin/activate
python -m backend.ingest
```

This fetches WINDFOR publications from December 29 through January 31, and FUELHH WIND actuals from January 2 through February 1. Four concurrent requests, bounded retries, and explicit timeouts are used. The normalized snapshot is replaced only after all fetches succeed. Restart the backend after a refresh because the snapshot is cached in memory. Ingestion is an offline build operation, not a public API route.

## Verify

```sh
source .venv/bin/activate
python -m pytest backend/tests -q
cd frontend
npm run build
```

The tests cover cutoff boundaries, future-publication exclusion, conflicts, missing half-hours, hidden actuals, mixed vintages, month boundaries, offset normalization, source filtering, actual revisions, independently calculated metrics, empty results, and API validation. API integration tests use the committed snapshot without network calls.

API routes: `/api/health`, `/api/metadata`, `/api/decision?day=2026-01-15&cutoff=10:00&actuals=false`, `/api/accuracy?start=2026-01-01&end=2026-01-31&cutoff=10:00`. OpenAPI is available at `/docs`.

## Deployment

The repository contains a Heroku container definition. The Docker image builds React and serves the generated assets through FastAPI on the injected `PORT`. Publish to a Heroku app configured for the container stack using this repository and `heroku.yml`. Hosting account access is required. The application does not need a database or API secret.

After deployment, replace the pending status above with the actual public URL and verify the core workflows while logged out. Docker container execution must also be checked on a machine with Docker Engine available; native Python/Node checks do not prove the container build.

## AI disclosure

I used Codex for product research, PRD finalization, and code completion.

## Remaining assignment deliverables

- Publish the code to a public GitHub repository with an anonymous/random name.
- Deploy publicly on Heroku or Vercel and add the URL here.
- Record and upload an unlisted YouTube video of no more than 10 minutes: customer section ≤5 minutes, technical section ≤5 minutes.
- Verify repository, deployment, and video access in incognito mode.
- Complete the submission form once its actual URL is supplied.

Do not submit without the video.
