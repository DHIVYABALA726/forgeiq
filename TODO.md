# ForgeIQ — Outcome Checklist

Acceptance clauses below preserve the requested product behavior. An outcome stays open until its behavior exists; checks are evidence, not substitute product scope.

## 1. Empty manufacturing workspace and navigation
- [x] On first launch, show an empty workspace with the exact message: “No manufacturing data available. Add jobs and machines to begin scheduling.” Never insert sample or fabricated data automatically.
- [x] An optional, clearly labelled **Load Sample Dataset** button loads deterministic, visibly labelled sample data for demonstration; sample data is removable and never loads automatically.
- [x] Display only meaningful workspace information: number of manually entered jobs, number of available machines, number of scheduled operations, and current schedule status. With no data, show zero counts and a helpful empty state; never show fake statistics.
- [x] Main navigation includes Manufacturing Data, Scheduling, Gantt Chart, Algorithm Comparison, and Scheduling Report. Prioritize data entry, configuration, Gantt, comparison and recommendation. Do not add unrelated modules.
- [x] Provide a clean professional industrial control-tower interface: light background, dark navy text, subtle blue accents, readable tables/charts, responsive layout, accessible form labels, simple left navigation, clear loading/success/warning/error states. Avoid unnecessary animation, excessive cards and decoration.

## 2. Manual jobs, machines and operations
- [x] Provide separate forms and CRUD views for jobs, machines and operations. Allow jobs to be created, edited, deleted, viewed, searched and filtered; allow machines and operations to be created, edited, deleted and viewed.
- [x] Job fields: unique Job ID; Job Name; Product Name; positive-integer Quantity; Priority (Critical, High, Medium, Low); Release Date and Time; Due Date and Time; optional notes. Required fields cannot be empty; IDs are unique; due date cannot precede release date.
- [x] Machine fields: unique Machine ID; Machine Name; Machine Type; Available From; optional Available Until; Availability status Available or Unavailable; optional setup time. Do not create machines automatically.
- [x] Operation fields: Operation ID; existing Job ID; Operation Name; Operation Sequence Number; one or multiple eligible existing machines; Processing Time in minutes; optional Setup Time in minutes; optional predecessor operation. Reject invalid references and negative or invalid durations.
- [x] Jobs may contain multiple ordered operations. Enforce precedence so an operation cannot begin until its predecessor finishes; multiple jobs can compete for machines, while no machine processes two operations simultaneously.
- [x] Support and clearly identify both **Job Shop Scheduling** (ordered operation sequence and eligible machines) and **Single-Operation / Parallel-Machine Scheduling**. Do not silently treat every job as single-operation.

## 3. Scheduling setup and algorithms
- [x] Users select the scheduling scenario, one or more algorithms, one primary objective and optional secondary objectives, then can use **Generate and Compare Schedules**. Run every selected applicable algorithm on the same manually entered dataset and applicable constraints.
- [x] Objectives: minimize makespan; minimize total tardiness; minimize maximum lateness; minimize number of tardy jobs; improve machine utilization; reduce average job waiting time.
- [x] Implement every algorithm that is selectable; do not display an unavailable/unimplemented algorithm. State supported scenarios and restrictions in the interface. Do not incorrectly apply single-machine sequencing rules to a general multi-machine job shop.
- [x] Implement FCFS (eligible jobs ordered by release-time/queue-arrival order), SPT (shortest eligible processing time), EDD (earliest due date), Priority-Based (configured priority order with documented release-time and due-date tie-breakers), and LPT (longest eligible processing time).
- [x] Implement NEH only for an explicitly supported permutation flow-shop scenario; do not claim it is a general or optimal job-shop solver. If that scenario is exposed, identify it explicitly rather than misrepresenting the two core scenarios.
- [x] For multi-operation job-shop scheduling, use valid precedence-aware and machine-capacity-aware scheduling logic; document heuristic limitations. Specify the solver and constraints if exact optimization is implemented; claim global optimality only if actually proved.
- [x] Every algorithm respects job release times, machine availability, operation precedence, machine capacity, eligible-machine restrictions and processing durations. Due dates are evaluation criteria unless an explicit hard-deadline constraint is configured. If algorithms cannot produce a feasible schedule, show the reason rather than generating an invalid Gantt chart.

## 4. Standard schedule results and real metrics
- [x] Every algorithm result provides algorithm name, scheduling scenario, scheduled operation IDs, job IDs, machine IDs, start/end times, processing durations, waiting times where applicable, due dates, completion times, constraint violations, feasibility status, objective values and actual measured computation time.
- [x] Use a consistent time representation, preferably minutes from a declared scheduling start time; convert it to readable dates and times in the interface.
- [x] Compare generated schedules in a table containing algorithm, feasible schedule, makespan, total completion time, total tardiness, maximum lateness, number of tardy jobs, average waiting time, machine utilization and computation time. Use N/A where a metric cannot meaningfully be calculated and explain definitions.
- [x] Calculate makespan as maximum operation completion minus scheduling-horizon start. Total completion time is the sum of job completion times using the documented time origin. Job tardiness is `max(0, completion time − due time)`. Maximum lateness is the maximum across jobs of `completion time − due time`. Tardy count counts jobs completing after due time.
- [x] Define average waiting from job/operation waiting intervals; do not confuse machine idle time with job waiting. Define machine utilization as productive processing time divided by available machine time over a declared horizon; exclude unavailable time and explain calculation. Computation time is actual backend elapsed time, never hardcoded.
- [x] Provide clear comparison charts for the selected objective and other useful metrics.

## 5. Interactive Gantt chart
- [x] Generate charts only from actual scheduling output. Provide a horizontal time axis and vertical rows grouped by machine, with separate bars for scheduled operations, job-distinct visual treatment, readable time labels, legend, idle-period handling and useful due-date indicators.
- [x] Each bar displays Job ID and operation name; each operation's details include Job ID, operation name, machine, start time, end time and duration. Tooltips show details on hover; selecting a task opens a side panel.
- [x] Provide zoom/time-scale controls, filters by job and machine, algorithm dropdown and a comparison mode that switches between schedules or shows them side-by-side. Do not use static example bars as actual results.

## 6. Deterministic recommendation
- [x] Recommend the most suitable algorithm for the entered production scenario only from actual results of selected algorithms. Validate inputs, run supported selected algorithms on identical data, reject infeasible results, compare feasible results using the primary objective and explicitly documented tie-breakers.
- [x] State exactly: “Recommended algorithm: [Algorithm Name]”; “Reason: [Measured result and comparison with alternatives]”; “Objective: [User-selected objective]”; “Scope: Best among the feasible algorithms evaluated for this dataset. This is not a guarantee of global optimality.”
- [x] Explain why recommendation changes when the objective changes, and describe the selected result using measured comparisons (e.g. lowest makespan/tardiness among feasible schedules evaluated, or configured tie-breaker for equivalent values). Never claim universally best.
- [x] Do not use an LLM or fabricated AI score to select a winner. Describe this as an algorithm-based recommendation system, not a trained AI model. If none is feasible, show a clear error and suggestions for fixing constraints.

## 7. User workflow, saved schedules and exports
- [x] The workflow is: open empty workspace; add machines manually; add jobs manually; add operations and machine eligibility; validate dataset; choose scenario; choose objective(s); select algorithms; generate schedules; view each Gantt; compare metrics; view recommendation and explanation; save selected schedule; export schedule and comparison report to CSV; provide printable report or PDF if practical; edit inputs and rerun.
- [x] Persist entered data so restarting does not erase it. Persist schedule runs, scheduled operations, algorithm results and recommendation details. Save an input dataset/version snapshot with each schedule so comparisons are reproducible.
- [x] Save and retrieve the selected schedule and its results. CSV export works for schedule and comparison report.
- [x] When relevant inputs change, mark previous results outdated; never silently display an old schedule as current.

## 8. REST API and persistence
- [x] Implement functional REST endpoints with appropriate validation, meaningful HTTP status codes and consistent JSON: GET/POST `/api/v1/jobs`, GET/PUT/DELETE `/api/v1/jobs/{job_id}`; GET/POST `/api/v1/machines`, PUT/DELETE `/api/v1/machines/{machine_id}`; GET/POST `/api/v1/operations`, PUT/DELETE `/api/v1/operations/{operation_id}`; POST `/api/v1/schedules/generate`; GET `/api/v1/schedules`; GET `/api/v1/schedules/{schedule_id}`; GET `/api/v1/schedules/{schedule_id}/comparison`; GET `/api/v1/schedules/{schedule_id}/gantt`; GET `/api/v1/schedules/{schedule_id}/recommendation`; GET `/api/v1/health`.
- [x] Backend returns actual scheduling-engine results. API documentation is available at `/docs` during local development. Frontend API base URL is configurable using `VITE_API_URL`; all frontend requests use it consistently. Configure local CORS and document secure production frontend-origin configuration.
- [x] Persist jobs, machines, operations, schedule runs, scheduled operations, algorithm results and recommendation details, including the hard-due-date constraint in each run's snapshot. Do not store secrets in the database or source code. Use SQLite at `backend/data/forgeiq.db` for simple local setup; if deployed with SQLite, mount durable storage at the same path (`/app/backend/data/forgeiq.db` in the container); otherwise recommend managed PostgreSQL for deployment. All external MySQL/PostgreSQL connections require verified TLS; never assume an ephemeral filesystem persists SQLite.

## 9. Validation and actionable error handling
- [x] Handle no jobs, no machines, nonexistent machine references, nonexistent job references, duplicate identifiers, negative processing times, invalid dates, impossible precedence, machine-capacity conflicts, unsupported scenarios and no feasible schedule.
- [x] Handle backend unavailable, invalid API response and failed schedule generation. Show meaningful user guidance rather than a generic “Failed to fetch” message.

## 10. Automated coverage and delivery documentation
- [x] Automated tests cover every implemented algorithm, precedence, machine capacity, release-time constraints, machine availability, due-date metric calculations, makespan, machine utilization, recommendation ranking, infeasible datasets and CRUD APIs.
- [x] Include deterministic test datasets with known expected results. Include an end-to-end manual-entry-to-Gantt workflow test where practical, verify each Gantt equals backend scheduled operations, and verify the recommendation matches the configured objective and tie-breakers.
- [x] Deliver complete, maintainable source for frontend, backend, scheduling engine, models, initialization, API routes, Gantt, comparison, recommendation, validations and tests—no “implement the remaining logic” placeholders.
- [x] Include dependency/package files, `.env.example`, `.gitignore`, and complete README with exact Windows 11 instructions for Python virtual environment creation/activation in CMD, dependency installation, database initialization, FastAPI start; Node install, API URL setup, Vite start and frontend production build.
- [x] Document GitHub/equivalent source setup, frontend deployment to Vercel/equivalent, backend to Render/equivalent, persistent production database/storage, deployment environment variables without secrets and production CORS. Do not claim tests passed unless actually run; report remaining failures honestly.
