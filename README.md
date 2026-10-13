# ForgeIQ — Intelligent Manufacturing Scheduling

ForgeIQ is a manual-entry manufacturing scheduling workbench. It runs real dispatching heuristics against entered job, machine and operation constraints, stores schedule snapshots, renders their actual operations in a Gantt chart, compares measured metrics, and transparently recommends the best feasible selected algorithm for the chosen objective. The recommender is deterministic; it is not a trained AI model.

## Features

- Empty first launch; no automatic sample data, fake KPIs or fabricated schedules. Use **Load Sample Dataset** only when you choose to; it is deterministic, marked **SAMPLE**, and removable.
- Full job, machine and ordered-operation entry, editing, viewing and deletion. Search and priority filters are available for jobs.
- Single-operation/parallel-machine and job-shop scheduling, plus a separately labelled permutation-flow-shop scenario for the NEH heuristic.
- FCFS, SPT, EDD, Priority-Based and LPT precedence-aware dispatch rules; NEH only for supported permutation flow shops. No global-optimality claim.
- Constraint validation, machine windows, setup time, job precedence and machine-capacity protection; infeasibility is explained rather than drawn as a valid schedule.
- Actual-output machine-row Gantt with filters, zoom, algorithm switching, tooltips and task details; comparison table, objective chart, measured recommendation and explanations.
- Saved/retrievable run snapshots, selected-algorithm save, CSV exports and printer-friendly report.
- FastAPI REST API and interactive API docs at `/docs`.

## Project layout

```text
forgeiq/
├── alembic.ini / backend/migrations/ # versioned, additive persistent schema
├── app.config.ts                    # ForgeIQ project logo metadata
├── backend/
│   ├── app/                 # FastAPI, SQLAlchemy models, API and scheduling engine
│   │   ├── api/routes.py
│   │   ├── scheduling/      # validation, heuristics, metrics and recommendation
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── migrations/          # versioned Alembic schema revisions
│   ├── tests/               # isolated SQLite, migration and API tests
│   └── requirements.txt
├── frontend/src/            # React/TypeScript pages, forms, Gantt, API client and styles
├── frontend/tests/          # Vitest/Testing Library interactions
├── public/manus-routes.json
├── Dockerfile
├── package.json / pnpm-lock.yaml
├── .env.example
└── README.md
```

## Requirements

- Python 3.11 or newer (validated with the included Python 3.12-compatible requirements).
- Node.js 22 LTS and Corepack/pnpm 11.25.0 (the version is pinned in `package.json`).
- Windows 11, macOS or Linux for local development.

## Local setup — Windows 11 CMD

Open a first Command Prompt in the repository root:

```bat
cd C:\path\to\forgeiq
corepack pnpm install
copy .env.example .env
```

Create and activate the Python environment, install dependencies, and apply the recorded local SQLite schema migration:

```bat
cd backend
py -3.11 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.init_db
```

Start the API (leave this terminal running):

```bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open a second Command Prompt in the repository root to run Vite:

```bat
cd C:\path\to\forgeiq
corepack pnpm dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). API calls use the relative `/api/v1` path; `vite.config.ts` proxies them to FastAPI. The default `.env.example` leaves `VITE_API_URL` blank for that proxy. The interactive API documentation is at `http://127.0.0.1:8000/docs`.

### Windows PowerShell equivalent

```powershell
Set-Location C:\path\to\forgeiq
corepack pnpm install
Copy-Item .env.example .env
Set-Location backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m app.init_db
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second PowerShell terminal, from the repository root:

```powershell
Set-Location C:\path\to\forgeiq
corepack pnpm dev
```

If PowerShell blocks virtual-environment activation, use CMD commands instead or run the Python executable by its full path; do not loosen machine-wide execution policy just for ForgeIQ.

## Build and serve the compiled frontend from FastAPI

Vite development mode is convenient for editing; the same FastAPI app can also serve the compiled React build and `/api/v1` on one origin:

```bat
cd C:\path\to\forgeiq
corepack pnpm build
cd backend
.venv\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 3000
```

Open `http://127.0.0.1:3000`. `http://127.0.0.1:3000/docs` remains available. If `frontend/dist` has not been built, FastAPI returns a setup message at `/` rather than a fake page.

## Configuration

Copy `.env.example` to `.env` and set only the values relevant to your environment. `VITE_API_URL` is the frontend API base, e.g. `https://forgeiq-api.example.com`; keep it blank for same-origin or Vite-proxied development. `VITE_API_PROXY_TARGET` changes the Vite development proxy (default `http://127.0.0.1:8000`). `CORS_ORIGINS` is a comma-separated list of exact origins. Keep `DATABASE_URL` empty to use a local SQLite file at `backend/data/forgeiq.db`, or set it to your selected MySQL-compatible or PostgreSQL connection string. External database connections require TLS: MySQL uses a certificate- and hostname-verified Python SSL context; PostgreSQL URLs are forced to `sslmode=verify-full`. For PostgreSQL providers with a private CA, configure `sslrootcert` to point to that trusted CA file; verification errors fail closed. Plaintext MySQL and PostgreSQL connections are never permitted. The additive Alembic migration is applied only when its revision is pending and records progress in `alembic_version`. Never commit `.env`, credentials or database dumps.

In the managed ForgeIQ preview, the platform's persistent database is selected through `DATABASE_URL`; it is separate from the local SQLite default. Preview development and its managed database may share state with a published service, so do not use sample data as a production seed. TLS verification is enforced for every external MySQL or PostgreSQL database URL.

## Scheduling behavior and metric definitions

- Times are normalized to UTC internally and the schedule horizon origin is the earliest entered job release time. Result operation times are minutes from that origin and include display-ready UTC timestamps.
- Operation occupancy includes its processing time, operation setup and the machine's configured setup time. Operations are non-preemptive. Job-shop dispatch rules make decisions only among precedence-ready operations and assigned machines; deterministic ties use release time, due time, priority, sequence and stable IDs as appropriate.
- FCFS orders eligible jobs by release/queue arrival. SPT/LPT use operation processing + setup duration. EDD uses the earliest job due time. Priority ranks Critical, High, Medium, Low, then uses release and due times. These rules are dispatching heuristics, not proofs of a global optimum.
- NEH is supported only when every job shares the same ordered sequence of distinct single-machine stages. The interface exposes it only in the explicitly named permutation-flow-shop mode.
- Makespan is final operation completion minus horizon origin. Total completion time sums each job's completion offset from the origin. Tardiness is `max(0, completion - due)`; maximum lateness retains negative (early) values; tardy count counts jobs whose completion exceeds due time.
- Average waiting is the average interval from job release/predecessor completion until an operation starts; it excludes machine idle time. Machine utilization is operation processing minutes divided by available machine minutes between the horizon origin and final completion; unavailable machine time and setup are excluded from the processing numerator. Computation time is actual backend elapsed time per algorithm.
- A machine is configured with one available-from / optional available-until window; the scheduler does not simulate multiple shift calendars or breakdowns. The due-date switch may make any run with a tardy job infeasible; otherwise due dates are evaluation criteria.
- Recommendations reject infeasible results, sort by the chosen objective (utilization higher is better; other objectives lower is better), then configured secondary objectives, then a stable alphabetical algorithm-name tie-break. A schedule's `dataset_version` and saved input snapshot make old results reproducible; changes in jobs/machines/operations flag those runs as outdated.

## REST API

All routes are under `/api/v1` and return JSON. FastAPI's generated reference is `/docs`.

| Method | Route | Purpose |
| --- | --- | --- |
| GET, POST | `/jobs` | List or create jobs |
| GET, PUT, DELETE | `/jobs/{job_id}` | Read, edit or remove a job |
| GET, POST | `/machines` | List or create machines |
| PUT, DELETE | `/machines/{machine_id}` | Edit or remove a machine; used machines cannot be deleted |
| GET, POST | `/operations` | List or create operations |
| PUT, DELETE | `/operations/{operation_id}` | Edit or remove an operation |
| POST | `/schedules/generate` | Validate input, run algorithms, persist results and recommendation |
| GET | `/schedules` | List saved runs (stale state is included) |
| GET | `/schedules/{schedule_id}` | Retrieve a run and input snapshot |
| GET | `/schedules/{schedule_id}/comparison` | Read calculated comparison metrics |
| GET | `/schedules/{schedule_id}/gantt?algorithm_name=SPT` | Read actual scheduled operations |
| GET | `/schedules/{schedule_id}/recommendation` | Read the deterministic recommendation and ranking |
| POST | `/schedules/{schedule_id}/select` | Save a feasible algorithm result as the selected schedule |
| GET | `/health` | Lightweight API status |
| GET | `/api/health` | Database-aware readiness check for containers |
| GET, DELETE | `/sample` | Explicitly load or remove only labelled deterministic sample records |

Job, machine and operation IDs are unique and stable (ID changes require delete/recreate). A job delete cascades its operations. A machine referenced by an operation cannot be deleted until the operation eligibility is edited. Sample records are tagged individually, and sample removal refuses to remove manually entered operations that depend on them.

## Automated tests

From the repository root:

```bat
cd backend
.venv\Scripts\activate.bat
pytest
```

From a separate repository-root terminal:

```bat
corepack pnpm test
corepack pnpm typecheck
corepack pnpm build
```

Backend API and migration tests use isolated in-memory SQLite (and API tests disable application-startup migrations), so they do not read or write the shared managed database. The Python suite covers strict MySQL/PostgreSQL TLS enforcement, the canonical SQLite path, recorded migrations, dispatch rules, NEH scope, precedence, machine capacity/availability, release constraints, metrics, infeasible inputs, saved hard-due context, recommendation ranking, sample-marker protection, CRUD, schedules and stale snapshots. Frontend interaction tests verify the exact empty first-launch state and explicit sample activation, infeasible workspace status, and saved-run algorithm selection.

Latest local checks: `pnpm build` succeeded; `pnpm test` passed (3 tests); `backend/.venv/bin/python -m pytest -q` passed (24 tests; one upstream Starlette/AnyIO deprecation warning); `pyright --project pyrightconfig.json` reported 0 errors; Python compile-only validation passed; and the documented local database initializer applied the Alembic revision to a disposable SQLite file that was then removed. Docker image build was not run in this Sandbox.

## Deployment — Vercel frontend + Render FastAPI backend

1. Create an empty GitHub repository (or equivalent Git host), then from the project root initialize/push this source tree using that host's documented authentication. With GitHub CLI (`gh`) already authenticated, an example is `git init && git add . && git commit -m "Build ForgeIQ manufacturing scheduler" && gh repo create forgeiq --source=. --public --push`. Choose `--private` if the source or manufacturing configuration is confidential. Never add `.env`, database files or credentials to Git.
2. Create a managed PostgreSQL database in Render (or a PostgreSQL provider that supplies a trusted server certificate). Configure the API service's server-side `DATABASE_URL` with its private connection string and provide the provider's trusted CA through `sslrootcert` when it is not in system roots. The app normalizes `postgres://`/`postgresql://` URLs to SQLAlchemy's psycopg driver and enforces `sslmode=verify-full`.
3. Create a Render Docker web service using this repository's `Dockerfile`; set health check path to `/api/health`. Render supplies `PORT`; the container listens on that value (default 3000). Attach the persistent Postgres service/connection URL rather than relying on container-local SQLite.
4. Set `CORS_ORIGINS` on the backend to the exact Vercel production origin (for example `https://your-forgeiq-project.vercel.app`) plus any explicitly needed preview origins. Do not use `*` in production.
5. Create a Vercel project from the repository. Use install command `corepack pnpm install --frozen-lockfile`, build command `corepack pnpm build`, root directory `.`, and output directory `frontend/dist`. Set the browser-safe `VITE_API_URL` to the deployed API origin, e.g. `https://your-forgeiq-api.onrender.com`, with no trailing slash.
6. Set `DATABASE_URL` and `CORS_ORIGINS` only as protected server environment values. Do not expose DB credentials through `VITE_*`. After changing backend CORS, restart/redeploy the API and verify `/api/health`, `/api/v1/health` and a browser CRUD request.

For a single-container deployment rather than separate Vercel/Render services, build the React bundle into `frontend/dist` and let FastAPI serve both the UI and APIs as in the Dockerfile. Configure persistent PostgreSQL all the same. The local SQLite default is `backend/data/forgeiq.db` (container path `/app/backend/data/forgeiq.db`); container-local file writes are not durable. Mount durable storage there if deliberately deploying SQLite; otherwise do not use SQLite on an ephemeral filesystem.
