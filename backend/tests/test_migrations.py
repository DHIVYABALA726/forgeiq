from __future__ import annotations
from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool


def test_initial_schema_migration_is_recorded_and_repeatable():
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "alembic.ini"
    test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    try:
        for _ in range(2):
            config = Config(str(config_path))
            with test_engine.connect() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
        names = set(inspect(test_engine).get_table_names())
        assert {"alembic_version", "dataset_state", "jobs", "machines", "operations", "schedule_runs", "algorithm_results", "scheduled_operations", "recommendations"}.issubset(names)
        with test_engine.connect() as connection:
            version = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one()
        assert version == "0001_initial_schema"
    finally:
        test_engine.dispose()
