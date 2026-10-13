from __future__ import annotations

from datetime import datetime, timezone, timedelta
from time import perf_counter
from collections import defaultdict
from .metrics import calculate_metrics
from .validation import as_utc, validate_dataset

ALGORITHMS = ["FCFS", "SPT", "EDD", "Priority-Based", "LPT", "NEH"]
PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class SchedulingError(ValueError):
    pass


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _prepare(jobs: list[dict], machines: list[dict], operations: list[dict]):
    releases = [as_utc(j["release_at"]) for j in jobs]
    horizon = min(releases)
    def minute(value):
        return (as_utc(value) - horizon).total_seconds() / 60
    job_data = {j["id"]: {**j, "release_minute": minute(j["release_at"]), "due_minute": minute(j["due_at"])} for j in jobs}
    machine_data = {m["id"]: {**m, "available_from_minute": minute(m["available_from"]), "available_until_minute": minute(m["available_until"]) if m.get("available_until") else None} for m in machines}
    op_data = [dict(op) for op in operations]
    by_job = defaultdict(list)
    for op in op_data:
        by_job[op["job_id"]].append(op)
    predecessor = {}
    for job_id, items in by_job.items():
        items.sort(key=lambda op: op["sequence"])
        previous = None
        for op in items:
            predecessor[op["id"]] = op.get("predecessor_id") or previous
            previous = op["id"]
    return job_data, machine_data, op_data, predecessor, horizon


def _rank(op: dict, job: dict, algorithm: str):
    base = (job["release_minute"], job["due_minute"], PRIORITY_ORDER.get(job["priority"], 9), op["sequence"], op["id"].casefold())
    duration = op["processing_time_minutes"] + op.get("setup_time_minutes", 0)
    if algorithm == "SPT": return (duration, *base)
    if algorithm == "LPT": return (-duration, *base)
    if algorithm == "EDD": return (job["due_minute"], *base)
    if algorithm == "Priority-Based": return (PRIORITY_ORDER.get(job["priority"], 9), *base)
    return base


def _find_machine_start(machine: dict, ready: float, duration: float, intervals: dict[str, list[tuple[float, float]]]):
    if not machine["is_available"]:
        return None
    start = max(ready, machine["available_from_minute"])
    limit = machine.get("available_until_minute")
    for begin, end in sorted(intervals[machine["id"]]):
        if start + duration <= begin + 1e-9:
            break
        if start < end - 1e-9:
            start = end
    if limit is not None and start + duration > limit + 1e-9:
        return None
    return start


def _flowshop_permutation(order: list[dict], jobs: dict, machines: dict, ops_by_job: dict[str, list[dict]], horizon: datetime):
    machine_tail = {mid: machines[mid]["available_from_minute"] for mid in machines}
    scheduled = []
    for job in order:
        previous_end = jobs[job["id"]]["release_minute"]
        for op in ops_by_job[job["id"]]:
            machine_id = op["eligible_machine_ids"][0]
            machine = machines[machine_id]
            if not machine["is_available"]:
                raise SchedulingError(f"Machine {machine_id} is unavailable.")
            duration = op["processing_time_minutes"] + op.get("setup_time_minutes", 0) + machine.get("setup_time_minutes", 0)
            start = max(previous_end, machine_tail[machine_id], machine["available_from_minute"])
            end = start + duration
            if machine.get("available_until_minute") is not None and end > machine["available_until_minute"] + 1e-9:
                raise SchedulingError(f"Operation {op['id']} cannot fit in machine {machine_id}'s available window.")
            due = jobs[job["id"]]["due_minute"]
            scheduled.append({"operation_id": op["id"], "job_id": job["id"], "machine_id": machine_id, "operation_name": op["name"], "sequence": op["sequence"], "start_minute": round(start, 4), "end_minute": round(end, 4), "processing_time_minutes": op["processing_time_minutes"], "setup_time_minutes": op.get("setup_time_minutes", 0) + machine.get("setup_time_minutes", 0), "duration_minutes": duration, "waiting_time_minutes": round(max(0, start - previous_end), 4), "due_minute": due, "due_at": _iso(as_utc(jobs[job["id"]]["due_at"])), "start_at": _iso(horizon + timedelta(minutes=start)), "end_at": _iso(horizon + timedelta(minutes=end))})
            machine_tail[machine_id] = end
            previous_end = end
    return scheduled


def _neh(jobs: dict, machines: dict, operations: list[dict], horizon: datetime):
    ops_by_job = defaultdict(list)
    for op in operations:
        ops_by_job[op["job_id"]].append(op)
    for items in ops_by_job.values(): items.sort(key=lambda op: op["sequence"])
    priority = sorted(jobs.values(), key=lambda job: (-sum(op["processing_time_minutes"] + op.get("setup_time_minutes", 0) for op in ops_by_job[job["id"]]), job["release_minute"], job["due_minute"], job["id"].casefold()))
    sequence: list[dict] = []
    for job in priority:
        best = None
        for position in range(len(sequence) + 1):
            candidate = [*sequence[:position], job, *sequence[position:]]
            result = _flowshop_permutation(candidate, jobs, machines, ops_by_job, horizon)
            makespan = max((item["end_minute"] for item in result), default=0)
            key = (makespan, tuple(x["id"].casefold() for x in candidate))
            if best is None or key < best[0]: best = (key, candidate)
        if best is None:
            raise RuntimeError("NEH failed to evaluate an insertion position.")
        sequence = best[1]
    return _flowshop_permutation(sequence, jobs, machines, ops_by_job, horizon)


def _dispatch(algorithm: str, jobs: dict, machines: dict, operations: list[dict], predecessor: dict, horizon: datetime):
    intervals = defaultdict(list)
    scheduled: list[dict] = []
    done: dict[str, float] = {}
    by_id = {op["id"]: op for op in operations}
    pending = set(by_id)
    while pending:
        options = []
        for op_id in pending:
            op = by_id[op_id]
            pred = predecessor.get(op_id)
            if pred and pred not in done:
                continue
            job = jobs[op["job_id"]]
            ready = max(job["release_minute"], done[pred] if pred else job["release_minute"])
            eligible = []
            for machine_id in sorted(set(op["eligible_machine_ids"])):
                machine = machines[machine_id]
                duration = op["processing_time_minutes"] + op.get("setup_time_minutes", 0) + machine.get("setup_time_minutes", 0)
                start = _find_machine_start(machine, ready, duration, intervals)
                if start is not None:
                    eligible.append((start, machine_id, duration, machine))
            if eligible:
                best_start = min(item[0] for item in eligible)
                machine_choice = min((item for item in eligible if abs(item[0] - best_start) < 1e-9), key=lambda item: item[1])
                options.append((best_start, _rank(op, job, algorithm), op_id, op, job, machine_choice, ready))
        if not options:
            blocked = []
            for op_id in sorted(pending):
                op = by_id[op_id]
                if not any(machines[mid]["is_available"] for mid in op["eligible_machine_ids"]):
                    blocked.append(f"Operation {op_id} has no available eligible machine.")
                elif predecessor.get(op_id) in pending:
                    blocked.append(f"Operation {op_id} is blocked by its predecessor.")
                else:
                    blocked.append(f"Operation {op_id} cannot fit within its eligible machine availability window.")
            raise SchedulingError(" ".join(blocked))
        earliest = min(item[0] for item in options)
        candidates = [item for item in options if abs(item[0] - earliest) < 1e-9]
        _, _, op_id, op, job, machine_choice, ready = min(candidates, key=lambda item: (item[1], item[2].casefold()))
        start, machine_id, duration, machine = machine_choice
        end = start + duration
        item = {"operation_id": op_id, "job_id": job["id"], "machine_id": machine_id, "operation_name": op["name"], "sequence": op["sequence"], "start_minute": round(start, 4), "end_minute": round(end, 4), "processing_time_minutes": op["processing_time_minutes"], "setup_time_minutes": op.get("setup_time_minutes", 0) + machine.get("setup_time_minutes", 0), "duration_minutes": duration, "waiting_time_minutes": round(max(0, start - ready), 4), "due_minute": job["due_minute"], "due_at": _iso(as_utc(job["due_at"])), "start_at": _iso(horizon + timedelta(minutes=start)), "end_at": _iso(horizon + timedelta(minutes=end))}
        scheduled.append(item)
        intervals[machine_id].append((start, end))
        done[op_id] = end
        pending.remove(op_id)
    return sorted(scheduled, key=lambda x: (x["start_minute"], x["machine_id"], x["operation_id"]))


def run_algorithm(algorithm: str, jobs: list[dict], machines: list[dict], operations: list[dict], scenario: str) -> dict:
    started = perf_counter()
    try:
        validate_dataset(jobs, machines, operations, scenario)
        if algorithm == "NEH" and scenario != "permutation_flow_shop":
            raise SchedulingError("NEH is only supported for the explicitly selected permutation-flow-shop scenario.")
        if scenario == "permutation_flow_shop" and algorithm != "NEH":
            raise SchedulingError("Permutation flow shop currently supports NEH only; select Job Shop or Parallel Machine for the dispatch rules.")
        prepared_jobs, prepared_machines, prepared_ops, predecessor, horizon = _prepare(jobs, machines, operations)
        scheduled = _neh(prepared_jobs, prepared_machines, prepared_ops, horizon) if algorithm == "NEH" else _dispatch(algorithm, prepared_jobs, prepared_machines, prepared_ops, predecessor, horizon)
        metrics = calculate_metrics(list(prepared_jobs.values()), list(prepared_machines.values()), scheduled, 0.0)
        return {"algorithm_name": algorithm, "scenario": scenario, "feasible": True, "scheduled_operations": scheduled, "metrics": metrics, "computation_time_ms": round((perf_counter() - started) * 1000, 4), "error_message": None}
    except (ValueError, KeyError) as exc:
        return {"algorithm_name": algorithm, "scenario": scenario, "feasible": False, "scheduled_operations": [], "metrics": {}, "computation_time_ms": round((perf_counter() - started) * 1000, 4), "error_message": str(exc)}
