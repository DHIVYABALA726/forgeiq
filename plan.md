# ForgeIQ — Implementation & Design Plan

## Product and architecture

ForgeIQ is a manual-input-first manufacturing scheduling workspace. It will show no fabricated operational data; sample data appears only after an explicit action and is deterministic, labelled and removable. The recommendation is a transparent ranking of actual feasible schedules, not a trained model or LLM output.

- **Frontend:** React, Vite, TypeScript, Tailwind CSS, Recharts, Lucide icons, custom SVG Gantt and browser tests for critical interactions. Accessible CRUD forms and responsive left-sidebar navigation.
- **Backend:** Python 3.11+, FastAPI, Pydantic, SQLAlchemy, Alembic and python-dotenv. A root `.env` is loaded for local use without overriding host-provided values. SQLAlchemy uses `backend/data/forgeiq.db` by default for Windows-local development; configured external database URLs support managed MySQL preview or production PostgreSQL with fail-closed certificate and hostname verification. A recorded additive Alembic migration runs at startup and through an explicit local init command; tests only use isolated SQLite and never touch the shared managed database.
- **Serving:** Vite development server proxies `/api` to FastAPI. In preview and packaged deployment, the compiled `frontend/dist` is served by FastAPI on configured port 3000 and API calls remain same-origin. Deployment notes cover Vercel static frontend with `VITE_API_URL`, Render/container FastAPI backend, persistent storage and managed PostgreSQL. CORS uses an explicit configurable origin list, not a permissive wildcard in production.
- **Persistence:** SQLAlchemy models for jobs, machines, operations, schedule runs, scheduled operations, algorithm results and recommendation details. Each run carries a versioned input snapshot. Mutations increment a dataset version; prior schedules remain retrievable but are clearly marked stale.
- **Scheduling engine:** Deterministic, event-time list scheduling for the parallel-machine and precedence-aware job-shop scenarios with machine eligibility, release times, machine calendar bounds, setup/processing durations and no machine overlap. FCFS, SPT, EDD, Priority and LPT choose from currently precedence-ready operations. A separate permutation-flow-shop mode makes NEH applicability explicit; NEH is never represented as a general job-shop optimizer. Metrics, tie-breaks, time origin, infeasibility reasons and limitations are documented in code and UI.
- **Reports:** Interactive machine-row Gantt generated from returned schedule records; algorithm comparison table/charts, deterministic recommendation, selected-run persistence, CSV exports and print stylesheet.
- **Validation:** pytest against isolated SQLite fixtures, frontend tests, type/build checks and API smoke checks. Report only checks actually run.

## Project structure

```text
forgeiq/
  plan.md, TODO.md, README.md, .gitignore, .env.example, alembic.ini, Dockerfile, .dockerignore
  package.json, pnpm-lock.yaml, index.html, vite.config.ts, tsconfig.json
  tailwind.config.js, postcss.config.js
  frontend/src/
    main.tsx, App.tsx, styles.css
    components/       sidebar and schedule-driven interactive Gantt
    pages/            workspace, manufacturing CRUD, scheduling, results/report
    services/         typed REST API client
    types/            frontend API/domain models
  public/manus-routes.json, public/favicon.svg
  backend/
    requirements.txt
    migrations/        Alembic environment and versioned schema revisions
    app/
      main.py, database.py, models.py, schemas.py, init_db.py
      api/             CRUD, schedules, health routes
      scheduling/      engine, algorithms, metrics, recommendation
    tests/             algorithm, constraint, metric, recommendation, API tests
```

## Scheduling rules and result semantics

- Dataset validation checks empty inputs, duplicate IDs, missing references, dates, positive durations, eligible available machines, sequence/predecessor consistency and cycles before any run.
- The two core scenarios are a single-operation parallel-machine problem and ordered job-shop scheduling. The extra permutation-flow-shop scenario is explicit so NEH has a supported, testable place; selection cards disclose scenario applicability.
- FCFS, SPT, EDD, Priority and LPT use deterministic documented tie-breakers and respect current eligibility, precedence and release/calendar constraints. For job-shop, priority rules guide ready-operation dispatch; they are heuristics, not optimality proofs. NEH is permutation-flow-shop only. A non-preemptive operation that cannot fit a machine's configured availability window is infeasible for that candidate; unavailable machines cannot be selected.
- All time values in a result are minutes from the declared scheduling-horizon origin. Operations have actual start/end/minutes, job/machine IDs and scenario; job completion is the final operation completion. Due dates are soft evaluation criteria unless explicitly defined otherwise.
- Metrics define makespan as last completion minus horizon origin; total completion as the sum of completion offsets from that origin; tardiness as positive completion-minus-due; max lateness as the maximum signed completion-minus-due; tardy count as jobs with positive lateness; waiting as accumulated job/operation queue intervals, excluding machine idle; utilization as productive time divided by the machine's available horizon after unavailable intervals. N/A is used where a denominator or comparison is not meaningful.
- The recommendation filters infeasible runs, ranks the selected primary metric in the correct direction, then uses documented deterministic tie-breaks (secondary objectives, followed by a stable algorithm-name ordering). The UI states the measured comparison, objective, and “Best among the feasible algorithms evaluated for this dataset. This is not a guarantee of global optimality.”

## Design system

- **Design movement:** Contemporary Swiss industrial instrumentation—orderly, high-contrast and precise, softened for day-to-day usability.
- **Core principles:** operational clarity over decoration; strong information hierarchy; visible constraints and traceability; consistent, accessible interactions.
- **Color philosophy:** warm near-white and pale steel surfaces reduce visual fatigue; deep navy anchors trust and legibility; clear cobalt is ForgeIQ's ownable action color; green/amber/red are reserved for true status and feasibility feedback.
- **Layout paradigm:** fixed, compact left rail and a broad workbench canvas. Data-entry and results use vertically structured, task-focused panels, not a decorative dashboard-card grid. The timeline takes the width it needs and scrolls horizontally when necessary.
- **Signature elements:** ForgeIQ wordmark with a simple interlocking forge/flow-line glyph; cobalt hairline section markers; monospaced time and metric labels reminiscent of calibrated controls.
- **Interaction philosophy:** edits are explicit, validated inline, and preserve user input after errors. Schedule runs have visible progress and current/outdated state. Selecting a Gantt bar opens its actual details; keyboard focus and labels remain visible.
- **Animation:** restrained 120–180 ms fades/position changes for navigation and status; no looping or distracting motion; respect `prefers-reduced-motion`; timeline zoom remains direct and predictable.
- **Typography system:** IBM Plex Sans for product/UI text with a clear semibold heading hierarchy; IBM Plex Mono for IDs, timestamps, durations and numeric metrics; robust system fallbacks.
- **Brand essence:** a dependable scheduling workbench that turns a manufacturer's entered constraints into inspectable, comparable plans; **precise, practical, transparent**.
- **Brand voice:** concise and operational, explaining outcomes without AI hype. Examples: “No manufacturing data available. Add jobs and machines to begin scheduling.” “SPT produced the lowest makespan among the feasible schedules evaluated.”
- **Wordmark & logo:** custom inline SVG mark formed by two linked production-flow segments inside a squared forge frame, paired with the ForgeIQ wordmark; no generic gear/photo decoration.
- **Signature brand color:** Forge cobalt `#2563EB`, reserved for primary actions, active navigation and selected schedule accents.

## Local and deployment workflow

The README will provide exact Windows 11 CMD and PowerShell commands to create/activate a Python virtual environment, install backend dependencies, apply the recorded Alembic schema revision/run the API and open `/docs`; install Node dependencies, configure `VITE_API_URL`, start Vite and produce the production build. It will explain how to run FastAPI serving the built app on one port as well as Vite/API separately during local development. It will cover Vercel/static frontend and Render/container backend deployment, environment variables, explicit CORS origins, persistent database/storage, PostgreSQL for production, and why an ephemeral-host SQLite file is not durable. `.env.example` contains placeholders only.

## Scope boundaries

No generic factory dashboard, auto-created machines/jobs, default sample records, fake statistics, hardcoded schedule/recommendation, random failures, AI chatbot, unrelated inventory/billing/payment/employee functions, fabricated ML, or nonfunctional controls. No claim of globally optimal job-shop schedules. Platform auto-publishing is off; this task builds and verifies a preview, not a public production release.
