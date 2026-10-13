from __future__ import annotations

from datetime import datetime, timezone
from typing import NoReturn
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session, selectinload
from ..database import get_db
from ..models import AlgorithmResult, DatasetState, Job, Machine, Operation, Recommendation, ScheduleRun, ScheduledOperation
from ..schemas import JobInput, MachineInput, OperationInput, ScheduleRequest, SelectScheduleInput
from ..scheduling.engine import run_algorithm
from ..scheduling.recommendation import rank_results
from ..scheduling.validation import DatasetError, validate_dataset

router = APIRouter(prefix="/api/v1")


def _iso(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _job_dict(item: Job) -> dict:
    return {"id": item.id, "name": item.name, "product_name": item.product_name, "quantity": item.quantity, "priority": item.priority, "release_at": _iso(item.release_at), "due_at": _iso(item.due_at), "notes": item.notes, "is_sample": item.is_sample}


def _machine_dict(item: Machine) -> dict:
    return {"id": item.id, "name": item.name, "machine_type": item.machine_type, "available_from": _iso(item.available_from), "available_until": _iso(item.available_until), "is_available": item.is_available, "setup_time_minutes": item.setup_time_minutes, "is_sample": item.is_sample}


def _operation_dict(item: Operation) -> dict:
    return {"id": item.id, "job_id": item.job_id, "name": item.name, "sequence": item.sequence, "eligible_machine_ids": item.eligible_machine_ids, "processing_time_minutes": item.processing_time_minutes, "setup_time_minutes": item.setup_time_minutes, "predecessor_id": item.predecessor_id, "is_sample": item.is_sample}


def _version(db: Session) -> int:
    state = db.get(DatasetState, 1)
    return state.version if state else 0


def _bump_version(db: Session) -> int:
    state = db.get(DatasetState, 1)
    if state is None:
        state = DatasetState(id=1, version=0)
        db.add(state)
    state.version += 1
    return state.version


def _not_found(entity: str, item_id: str) -> NoReturn:
    raise HTTPException(status_code=404, detail=f"{entity} {item_id} was not found.")


def _new_or_update(model, payload):
    return payload.model_dump()


def _run_payload(run: ScheduleRun, db: Session, include_snapshot: bool = False) -> dict:
    current_version = _version(db)
    results = []
    for result in run.results:
        operations = result.result_payload.get("scheduled_operations", []) if result.feasible else []
        metrics = result.metrics if result.feasible else {}
        violations = [] if result.feasible else [result.error_message or "No feasible schedule was produced for this algorithm."]
        results.append({"algorithm_name": result.algorithm_name, "scenario": run.scenario, "feasible": result.feasible, "scheduled_operations": operations, "metrics": metrics, "objective_value": metrics.get(run.objective), "constraint_violations": violations, "computation_time_ms": result.computation_time_ms, "error_message": result.error_message})
    recommendation = run.recommendation
    payload = {"id": run.id, "scenario": run.scenario, "objective": run.objective, "secondary_objectives": run.secondary_objectives, "hard_due_dates": bool(run.input_snapshot.get("hard_due_dates", False)), "dataset_version": run.dataset_version, "current_dataset_version": current_version, "is_stale": run.dataset_version != current_version, "created_at": _iso(run.created_at), "selected_algorithm_name": run.selected_algorithm_name, "recommended_algorithm_name": recommendation.recommended_algorithm_name if recommendation else None, "recommendation_reason": recommendation.reason if recommendation else None, "recommendation_details": recommendation.details if recommendation else {}, "results": results}
    if include_snapshot:
        payload["input_snapshot"] = run.input_snapshot
    return payload


@router.get("/health")
def health():
    return {"status": "ok", "service": "forgeiq-api"}


@router.get("/dataset-version")
def dataset_version(db: Session = Depends(get_db)):
    return {"version": _version(db)}


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return {"items": [_job_dict(x) for x in db.scalars(select(Job).order_by(Job.id)).all()]}


@router.post("/jobs", status_code=status.HTTP_201_CREATED)
def create_job(payload: JobInput, db: Session = Depends(get_db)):
    if db.get(Job, payload.id):
        raise HTTPException(409, f"Job ID {payload.id} already exists.")
    item = Job(**_new_or_update(Job, payload))
    db.add(item); _bump_version(db); db.commit(); db.refresh(item)
    return _job_dict(item)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    item = db.get(Job, job_id)
    if not item: _not_found("Job", job_id)
    return _job_dict(item)


@router.put("/jobs/{job_id}")
def update_job(job_id: str, payload: JobInput, db: Session = Depends(get_db)):
    item = db.get(Job, job_id)
    if not item: _not_found("Job", job_id)
    if payload.id != job_id and db.get(Job, payload.id): raise HTTPException(409, f"Job ID {payload.id} already exists.")
    if payload.id != job_id: raise HTTPException(422, "Job IDs cannot be changed. Delete this job and recreate it with the new ID.")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    _bump_version(db); db.commit(); db.refresh(item)
    return _job_dict(item)


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    item = db.get(Job, job_id)
    if not item: _not_found("Job", job_id)
    db.delete(item); _bump_version(db); db.commit()
    return None


@router.get("/machines")
def list_machines(db: Session = Depends(get_db)):
    return {"items": [_machine_dict(x) for x in db.scalars(select(Machine).order_by(Machine.id)).all()]}


@router.post("/machines", status_code=201)
def create_machine(payload: MachineInput, db: Session = Depends(get_db)):
    if db.get(Machine, payload.id): raise HTTPException(409, f"Machine ID {payload.id} already exists.")
    item = Machine(**payload.model_dump()); db.add(item); _bump_version(db); db.commit(); db.refresh(item)
    return _machine_dict(item)


@router.put("/machines/{machine_id}")
def update_machine(machine_id: str, payload: MachineInput, db: Session = Depends(get_db)):
    item = db.get(Machine, machine_id)
    if not item: _not_found("Machine", machine_id)
    if payload.id != machine_id: raise HTTPException(422, "Machine IDs cannot be changed. Delete and recreate the machine to use another ID.")
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    _bump_version(db); db.commit(); db.refresh(item)
    return _machine_dict(item)


@router.delete("/machines/{machine_id}", status_code=204)
def delete_machine(machine_id: str, db: Session = Depends(get_db)):
    item = db.get(Machine, machine_id)
    if not item: _not_found("Machine", machine_id)
    used = [o.id for o in db.scalars(select(Operation)).all() if machine_id in (o.eligible_machine_ids or [])]
    if used: raise HTTPException(409, f"Machine {machine_id} is referenced by operation(s) {', '.join(used)}. Edit those operations before deleting the machine.")
    db.delete(item); _bump_version(db); db.commit()
    return None


@router.get("/operations")
def list_operations(db: Session = Depends(get_db)):
    return {"items": [_operation_dict(x) for x in db.scalars(select(Operation).order_by(Operation.job_id, Operation.sequence, Operation.id)).all()]}


def _validate_operation(payload: OperationInput, db: Session, current_id: str | None = None):
    if not db.get(Job, payload.job_id): raise HTTPException(422, f"Operation refers to missing job {payload.job_id}.")
    previous = db.scalar(select(Operation).where(Operation.job_id == payload.job_id, Operation.sequence < payload.sequence, Operation.id != (current_id or "")).order_by(Operation.sequence.desc()).limit(1))
    if payload.predecessor_id and (previous is None or payload.predecessor_id != previous.id):
        raise HTTPException(422, "Predecessor must be the immediately previous operation in this job's sequence.")
    if payload.predecessor_id:
        pred = db.get(Operation, payload.predecessor_id)
        if not pred and payload.predecessor_id != current_id: raise HTTPException(422, f"Predecessor operation {payload.predecessor_id} does not exist.")
        if pred and (pred.job_id != payload.job_id or pred.sequence >= payload.sequence): raise HTTPException(422, "Predecessor must be an earlier operation in the same job.")
    missing = [mid for mid in set(payload.eligible_machine_ids) if not db.get(Machine, mid)]
    if missing: raise HTTPException(422, f"Unknown eligible machine(s): {', '.join(missing)}.")
    duplicate_sequence = db.scalar(select(Operation).where(Operation.job_id == payload.job_id, Operation.sequence == payload.sequence, Operation.id != (current_id or "")))
    if duplicate_sequence: raise HTTPException(409, f"Job {payload.job_id} already has an operation at sequence {payload.sequence}.")


@router.post("/operations", status_code=201)
def create_operation(payload: OperationInput, db: Session = Depends(get_db)):
    if db.get(Operation, payload.id): raise HTTPException(409, f"Operation ID {payload.id} already exists.")
    _validate_operation(payload, db)
    item = Operation(**payload.model_dump()); db.add(item); _bump_version(db); db.commit(); db.refresh(item)
    return _operation_dict(item)


@router.put("/operations/{operation_id}")
def update_operation(operation_id: str, payload: OperationInput, db: Session = Depends(get_db)):
    item = db.get(Operation, operation_id)
    if not item: _not_found("Operation", operation_id)
    if payload.id != operation_id: raise HTTPException(422, "Operation IDs cannot be changed. Delete and recreate the operation with the new ID.")
    _validate_operation(payload, db, operation_id)
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    _bump_version(db); db.commit(); db.refresh(item)
    return _operation_dict(item)


@router.delete("/operations/{operation_id}", status_code=204)
def delete_operation(operation_id: str, db: Session = Depends(get_db)):
    item = db.get(Operation, operation_id)
    if not item: _not_found("Operation", operation_id)
    dependents = db.scalars(select(Operation).where(Operation.predecessor_id == operation_id)).all()
    if dependents: raise HTTPException(409, f"Operation {operation_id} is a predecessor of {', '.join(x.id for x in dependents)}. Edit those operations before deleting it.")
    db.delete(item); _bump_version(db); db.commit()
    return None


@router.post("/sample", status_code=201)
def load_sample(db: Session = Depends(get_db)):
    if db.scalar(select(Job.id).limit(1)) or db.scalar(select(Machine.id).limit(1)):
        raise HTTPException(409, "Sample data can only be loaded into an empty workspace. Remove existing entries or create your own data.")
    stamp = "2030-01-15T08:00:00+00:00"
    machines = [Machine(id="M-101", name="Precision Mill", machine_type="Milling", available_from=datetime.fromisoformat(stamp), is_available=True, setup_time_minutes=0, is_sample=True), Machine(id="M-102", name="CNC Drill", machine_type="Drilling", available_from=datetime.fromisoformat(stamp), is_available=True, setup_time_minutes=0, is_sample=True), Machine(id="M-103", name="Assembly Cell", machine_type="Assembly", available_from=datetime.fromisoformat(stamp), is_available=True, setup_time_minutes=0, is_sample=True)]
    jobs = [Job(id="J-201", name="Bracket batch", product_name="Mounting bracket", quantity=24, priority="High", release_at=datetime.fromisoformat(stamp), due_at=datetime.fromisoformat("2030-01-15T12:00:00+00:00"), notes="Deterministic demonstration sample", is_sample=True), Job(id="J-202", name="Housing batch", product_name="Drive housing", quantity=12, priority="Medium", release_at=datetime.fromisoformat("2030-01-15T08:20:00+00:00"), due_at=datetime.fromisoformat("2030-01-15T15:00:00+00:00"), notes="Deterministic demonstration sample", is_sample=True), Job(id="J-203", name="Rotor batch", product_name="Rotor assembly", quantity=8, priority="Critical", release_at=datetime.fromisoformat("2030-01-15T08:10:00+00:00"), due_at=datetime.fromisoformat("2030-01-15T11:30:00+00:00"), notes="Deterministic demonstration sample", is_sample=True)]
    ops = [
        Operation(id="OP-201-1", job_id="J-201", name="Milling", sequence=1, eligible_machine_ids=["M-101"], processing_time_minutes=42, setup_time_minutes=5, is_sample=True),
        Operation(id="OP-201-2", job_id="J-201", name="Drilling", sequence=2, eligible_machine_ids=["M-102"], processing_time_minutes=24, setup_time_minutes=0, predecessor_id="OP-201-1", is_sample=True),
        Operation(id="OP-201-3", job_id="J-201", name="Assembly", sequence=3, eligible_machine_ids=["M-103"], processing_time_minutes=36, setup_time_minutes=3, predecessor_id="OP-201-2", is_sample=True),
        Operation(id="OP-202-1", job_id="J-202", name="Milling", sequence=1, eligible_machine_ids=["M-101"], processing_time_minutes=29, setup_time_minutes=0, is_sample=True),
        Operation(id="OP-202-2", job_id="J-202", name="Drilling", sequence=2, eligible_machine_ids=["M-102"], processing_time_minutes=22, setup_time_minutes=0, predecessor_id="OP-202-1", is_sample=True),
        Operation(id="OP-202-3", job_id="J-202", name="Assembly", sequence=3, eligible_machine_ids=["M-103"], processing_time_minutes=48, setup_time_minutes=0, predecessor_id="OP-202-2", is_sample=True),
        Operation(id="OP-203-1", job_id="J-203", name="Milling", sequence=1, eligible_machine_ids=["M-101"], processing_time_minutes=35, setup_time_minutes=2, is_sample=True),
        Operation(id="OP-203-2", job_id="J-203", name="Drilling", sequence=2, eligible_machine_ids=["M-102"], processing_time_minutes=18, setup_time_minutes=0, predecessor_id="OP-203-1", is_sample=True),
        Operation(id="OP-203-3", job_id="J-203", name="Assembly", sequence=3, eligible_machine_ids=["M-103"], processing_time_minutes=30, setup_time_minutes=0, predecessor_id="OP-203-2", is_sample=True),
    ]
    db.add_all([*machines, *jobs, *ops]); _bump_version(db); db.commit()
    return {"message": "Deterministic sample dataset loaded. Sample records are labelled and can be removed.", "jobs": len(jobs), "machines": len(machines), "operations": len(ops)}


@router.delete("/sample")
def remove_sample(db: Session = Depends(get_db)):
    sample_jobs = set(db.scalars(select(Job.id).where(Job.is_sample.is_(True))).all())
    sample_machines = set(db.scalars(select(Machine.id).where(Machine.is_sample.is_(True))).all())
    if not sample_jobs and not sample_machines: raise HTTPException(404, "No labelled sample dataset is loaded.")
    user_ops = db.scalars(select(Operation).where(Operation.is_sample.is_(False))).all()
    blockers = [op.id for op in user_ops if op.job_id in sample_jobs or sample_machines.intersection(op.eligible_machine_ids or [])]
    if blockers: raise HTTPException(409, f"Sample data is referenced by manually entered operation(s): {', '.join(blockers)}. Edit or remove them before removing the sample.")
    db.execute(delete(Operation).where(Operation.is_sample.is_(True)))
    for job_id in sample_jobs:
        item = db.get(Job, job_id)
        if item: db.delete(item)
    for machine_id in sample_machines:
        item = db.get(Machine, machine_id)
        if item: db.delete(item)
    _bump_version(db); db.commit()
    return {"message": "Labelled sample records removed."}


def _snapshot(db: Session):
    jobs = [_job_dict(x) for x in db.scalars(select(Job).order_by(Job.id)).all()]
    machines = [_machine_dict(x) for x in db.scalars(select(Machine).order_by(Machine.id)).all()]
    operations = [_operation_dict(x) for x in db.scalars(select(Operation).order_by(Operation.job_id, Operation.sequence)).all()]
    return jobs, machines, operations


@router.post("/schedules/generate", status_code=201)
def generate_schedules(request: ScheduleRequest, db: Session = Depends(get_db)):
    jobs, machines, operations = _snapshot(db)
    try:
        validate_dataset(jobs, machines, operations, request.scenario)
    except DatasetError as exc:
        raise HTTPException(422, str(exc)) from exc
    if request.scenario == "permutation_flow_shop" and any(name != "NEH" for name in request.algorithms):
        raise HTTPException(422, "Permutation flow shop currently supports NEH only. Remove other algorithms or choose a supported scenario.")
    if request.scenario != "permutation_flow_shop" and "NEH" in request.algorithms:
        raise HTTPException(422, "NEH requires the explicitly supported permutation-flow-shop scenario; remove NEH or change the scenario.")
    run_id = str(uuid4()); dataset_version = _version(db)
    results = [run_algorithm(name, jobs, machines, operations, request.scenario) for name in request.algorithms]
    for result in results:
        if request.hard_due_dates and result["feasible"]:
            late = [jid for jid, value in result["metrics"].get("job_lateness_minutes", {}).items() if value > 0]
            if late:
                result["feasible"] = False
                result["error_message"] = f"Hard due-date constraint violated by job(s): {', '.join(sorted(late))}."
    winner, reason, ranking = rank_results(results, request.objective, request.secondary_objectives)
    run = ScheduleRun(id=run_id, scenario=request.scenario, objective=request.objective, secondary_objectives=request.secondary_objectives, dataset_version=dataset_version, input_snapshot={"jobs": jobs, "machines": machines, "operations": operations, "scenario": request.scenario, "horizon_start": min(x["release_at"] for x in jobs), "hard_due_dates": request.hard_due_dates}, selected_algorithm_name=None)
    db.add(run)
    db.flush()
    for item in results:
        payload = {"scheduled_operations": item.get("scheduled_operations", [])}
        result_row = AlgorithmResult(run_id=run_id, algorithm_name=item["algorithm_name"], feasible=item["feasible"], metrics=item.get("metrics", {}), result_payload=payload, computation_time_ms=item["computation_time_ms"], error_message=item.get("error_message"))
        db.add(result_row); db.flush()
        for op in item.get("scheduled_operations", []):
            db.add(ScheduledOperation(result_id=result_row.id, operation_id=op["operation_id"], job_id=op["job_id"], machine_id=op["machine_id"], operation_name=op["operation_name"], sequence=op["sequence"], start_minute=op["start_minute"], end_minute=op["end_minute"], processing_time_minutes=op["processing_time_minutes"], setup_time_minutes=op["setup_time_minutes"], waiting_time_minutes=op["waiting_time_minutes"], due_at=op["due_at"], start_at=op["start_at"], end_at=op["end_at"]))
    db.add(Recommendation(run_id=run_id, recommended_algorithm_name=winner, reason=reason, details={"objective": request.objective, "secondary_objectives": request.secondary_objectives, "hard_due_dates": request.hard_due_dates, "ranking": ranking, "scope": "Best among the feasible algorithms evaluated for this dataset. This is not a guarantee of global optimality."}))
    db.commit()
    stored = db.scalar(select(ScheduleRun).where(ScheduleRun.id == run_id).options(selectinload(ScheduleRun.results), selectinload(ScheduleRun.recommendation)))
    if stored is None:
        _not_found("Schedule", run_id)
    return _run_payload(stored, db, True)


@router.get("/schedules")
def list_schedules(db: Session = Depends(get_db)):
    runs = db.scalars(select(ScheduleRun).order_by(ScheduleRun.created_at.desc())).all()
    return {"items": [_run_payload(run, db) for run in runs]}


@router.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    run = db.scalar(select(ScheduleRun).where(ScheduleRun.id == schedule_id).options(selectinload(ScheduleRun.results), selectinload(ScheduleRun.recommendation)))
    if not run: _not_found("Schedule", schedule_id)
    return _run_payload(run, db, True)


@router.get("/schedules/{schedule_id}/comparison")
def get_comparison(schedule_id: str, db: Session = Depends(get_db)):
    run = db.scalar(select(ScheduleRun).where(ScheduleRun.id == schedule_id).options(selectinload(ScheduleRun.results)))
    if not run: _not_found("Schedule", schedule_id)
    return {"schedule_id": run.id, "objective": run.objective, "hard_due_dates": bool(run.input_snapshot.get("hard_due_dates", False)), "algorithms": [{"algorithm_name": x.algorithm_name, "feasible": x.feasible, "metrics": x.metrics if x.feasible else {}, "objective_value": x.metrics.get(run.objective) if x.feasible else None, "constraint_violations": [] if x.feasible else [x.error_message or "No feasible schedule was produced for this algorithm."], "computation_time_ms": x.computation_time_ms, "error_message": x.error_message} for x in run.results]}


@router.get("/schedules/{schedule_id}/gantt")
def get_gantt(schedule_id: str, algorithm_name: str | None = Query(default=None), db: Session = Depends(get_db)):
    run = db.scalar(select(ScheduleRun).where(ScheduleRun.id == schedule_id).options(selectinload(ScheduleRun.results), selectinload(ScheduleRun.recommendation)))
    if not run: _not_found("Schedule", schedule_id)
    selected = algorithm_name or run.selected_algorithm_name or (run.recommendation.recommended_algorithm_name if run.recommendation else None)
    result = next((x for x in run.results if x.algorithm_name == selected), None)
    if not result: raise HTTPException(404, f"No schedule result found for algorithm {selected or '(not selected)'}." )
    if not result.feasible: raise HTTPException(422, result.error_message or "This algorithm did not produce a feasible schedule; no Gantt is available.")
    return {"schedule_id": run.id, "algorithm_name": result.algorithm_name, "scenario": run.scenario, "feasible": result.feasible, "scheduled_operations": result.result_payload.get("scheduled_operations", [])}


@router.get("/schedules/{schedule_id}/recommendation")
def get_recommendation(schedule_id: str, db: Session = Depends(get_db)):
    run = db.scalar(select(ScheduleRun).where(ScheduleRun.id == schedule_id).options(selectinload(ScheduleRun.recommendation)))
    if not run: _not_found("Schedule", schedule_id)
    if not run.recommendation: raise HTTPException(404, "Recommendation details are unavailable for this schedule.")
    return {"recommended_algorithm_name": run.recommendation.recommended_algorithm_name, "reason": run.recommendation.reason, "objective": run.objective, "hard_due_dates": bool(run.input_snapshot.get("hard_due_dates", False)), "scope": run.recommendation.details.get("scope"), "ranking": run.recommendation.details.get("ranking", []), "is_stale": run.dataset_version != _version(db)}


@router.post("/schedules/{schedule_id}/select")
def select_saved_schedule(schedule_id: str, payload: SelectScheduleInput, db: Session = Depends(get_db)):
    run = db.scalar(select(ScheduleRun).where(ScheduleRun.id == schedule_id).options(selectinload(ScheduleRun.results), selectinload(ScheduleRun.recommendation)))
    if not run: _not_found("Schedule", schedule_id)
    result = next((x for x in run.results if x.algorithm_name == payload.algorithm_name and x.feasible), None)
    if not result: raise HTTPException(422, "Choose a feasible algorithm result to save as the selected schedule.")
    run.selected_algorithm_name = payload.algorithm_name
    db.commit(); db.refresh(run)
    return {"schedule_id": run.id, "selected_algorithm_name": run.selected_algorithm_name, "is_stale": run.dataset_version != _version(db)}
