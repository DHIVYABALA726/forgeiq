from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

Priority = Literal["Critical", "High", "Medium", "Low"]
Scenario = Literal["parallel_machine", "job_shop", "permutation_flow_shop"]
Objective = Literal["makespan", "total_tardiness", "maximum_lateness", "tardy_jobs", "machine_utilization", "average_waiting"]
Algorithm = Literal["FCFS", "SPT", "EDD", "Priority-Based", "LPT", "NEH"]


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class JobInput(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    product_name: str = Field(min_length=1, max_length=160)
    quantity: int = Field(gt=0)
    priority: Priority
    release_at: datetime
    due_at: datetime
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("release_at", "due_at")
    @classmethod
    def normalize_dates(cls, value: datetime) -> datetime:
        return normalize_datetime(value)

    @model_validator(mode="after")
    def valid_dates(self):
        if self.due_at < self.release_at:
            raise ValueError("Due date must not precede the release date.")
        return self


class MachineInput(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    machine_type: str = Field(min_length=1, max_length=120)
    available_from: datetime
    available_until: datetime | None = None
    is_available: bool = True
    setup_time_minutes: int = Field(default=0, ge=0)

    @field_validator("available_from", "available_until")
    @classmethod
    def normalize_dates(cls, value: datetime | None):
        return normalize_datetime(value) if value else None

    @model_validator(mode="after")
    def valid_window(self):
        if self.available_until and self.available_until <= self.available_from:
            raise ValueError("Available Until must be later than Available From.")
        return self


class OperationInput(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    job_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    sequence: int = Field(gt=0)
    eligible_machine_ids: list[str] = Field(min_length=1)
    processing_time_minutes: int = Field(gt=0)
    setup_time_minutes: int = Field(default=0, ge=0)
    predecessor_id: str | None = None


class ScheduleRequest(BaseModel):
    scenario: Scenario
    algorithms: list[Algorithm] = Field(min_length=1)
    objective: Objective
    secondary_objectives: list[Objective] = Field(default_factory=list)
    hard_due_dates: bool = False

    @field_validator("algorithms")
    @classmethod
    def unique_algorithms(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Select each scheduling algorithm only once.")
        return value

    @field_validator("secondary_objectives")
    @classmethod
    def distinct_secondary(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Select each secondary objective only once.")
        return value


class SelectScheduleInput(BaseModel):
    algorithm_name: Algorithm
