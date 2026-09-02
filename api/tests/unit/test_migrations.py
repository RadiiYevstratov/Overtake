"""Migrations must produce exactly the schema the models describe.

This caught a real bug: the generated DDL was indented one level too far and
ended up inside a `if dialect == 'postgresql'` guard, so `alembic upgrade head`
reported success while creating no tables at all on SQLite.
"""

from __future__ import annotations

import pathlib
import tempfile

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from alembic import command
from overtake.models import Base

API_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _alembic_config(url: str) -> Config:
    cfg = Config(str(API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="module")
def migrated_inspector():
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "migrated.db"
        sync_url = f"sqlite:///{path.as_posix()}"
        command.upgrade(_alembic_config(f"sqlite+aiosqlite:///{path.as_posix()}"), "head")
        engine = create_engine(sync_url)
        try:
            with engine.connect() as conn:
                yield inspect(conn)
        finally:
            engine.dispose()


def test_migration_creates_every_table(migrated_inspector):
    migrated = set(migrated_inspector.get_table_names()) - {"alembic_version"}
    assert migrated == set(Base.metadata.tables), "migration and models disagree on tables"


def test_migration_creates_every_column(migrated_inspector):
    problems = []
    for name, table in sorted(Base.metadata.tables.items()):
        migrated_cols = {c["name"] for c in migrated_inspector.get_columns(name)}
        model_cols = set(table.columns.keys())
        if migrated_cols != model_cols:
            problems.append(
                f"{name}: missing={model_cols - migrated_cols} extra={migrated_cols - model_cols}"
            )
    assert not problems, "; ".join(problems)


def test_autoincrement_primary_keys_actually_autoincrement(migrated_inspector):
    """SQLite only auto-increments a column declared exactly INTEGER PRIMARY KEY."""
    checked = 0
    for name, table in sorted(Base.metadata.tables.items()):
        pk_cols = list(table.primary_key.columns)
        if len(pk_cols) != 1:
            continue
        pk = pk_cols[0]
        # Only server-generated integer keys are at risk; natural keys such as
        # an FPL element id or a token hash are supplied by us.
        if pk.autoincrement is not True or pk.type.python_type is not int:
            continue
        col = next(c for c in migrated_inspector.get_columns(name) if c["name"] == pk.name)
        assert str(col["type"]).upper() == "INTEGER", (
            f"{name}.{pk.name} renders as {col['type']}; SQLite will not "
            "auto-increment anything but INTEGER PRIMARY KEY"
        )
        checked += 1
    assert checked >= 4, "expected several generated integer primary keys to check"


def test_baseline_downgrade_is_refused():
    """The baseline drops every table; that must never be a one-command mistake."""
    spec = API_ROOT / "alembic/versions/0001_baseline.py"
    source = spec.read_text(encoding="utf-8")
    assert "raise RuntimeError" in source
    assert "def downgrade()" in source


def test_generated_ddl_is_not_inside_a_dialect_guard():
    source = (API_ROOT / "alembic/versions/0001_baseline.py").read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.strip().startswith("op.create_table"):
            assert line.startswith("    op.create_table"), (
                "create_table must run for every dialect, not only PostgreSQL"
            )
