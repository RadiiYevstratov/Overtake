"""What the database is actually asked to send.

`.first()` on a Core result throws rows away *after* the server has sent them,
so a single-row read written without `LIMIT` quietly pays to transfer every row
it ignores. On `simulations`, where each row carries a results blob, that read
sat on the path of every board, brief and dossier view and grew by one row per
gameweek — it exhausted a 5 GB monthly transfer allowance in two weeks.

These tests assert the shape of the query rather than its answer, because the
answer was always right. That is precisely why nothing else caught it.
"""

from __future__ import annotations

import pytest
from sqlalchemy import event

from overtake.services.dossier_service import latest_squad
from overtake.services.league_service import (
    get_current_gameweek,
    get_next_gameweek,
    latest_simulation,
    latest_simulation_ref,
)


@pytest.fixture
def statements(engine):
    """Every SQL statement the engine emits during the test."""
    seen: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        seen.append(" ".join(statement.split()))

    event.listen(engine.sync_engine, "after_cursor_execute", record)
    yield seen
    event.remove(engine.sync_engine, "after_cursor_execute", record)


def reads_of(statements: list[str], table: str) -> list[str]:
    return [s for s in statements if s.lower().startswith("select") and table in s.lower()]


class TestSingleRowReadsAreLimited:
    async def test_the_newest_simulation_is_one_row(self, db, statements):
        await latest_simulation(db, 1)
        [sql] = reads_of(statements, "simulations")
        assert "LIMIT" in sql.upper()

    async def test_the_simulation_reference_reads_no_results_blob(self, db, statements):
        """Callers that only need which simulation is current never load one."""
        await latest_simulation_ref(db, 1)
        [sql] = reads_of(statements, "simulations")
        assert "LIMIT" in sql.upper()
        assert "results" not in sql.lower()

    async def test_the_newest_squad_is_one_row(self, db, statements):
        await latest_squad(db, 1)
        [sql] = reads_of(statements, "manager_picks")
        assert "LIMIT" in sql.upper()

    @pytest.mark.parametrize("helper", [get_current_gameweek, get_next_gameweek])
    async def test_gameweek_lookups_are_one_row(self, db, statements, helper):
        await helper(db)
        ordered = [sql for sql in reads_of(statements, "gameweeks") if "order by" in sql.lower()]
        assert ordered, "expected the fallback lookup to run on an empty table"
        assert all("LIMIT" in sql.upper() for sql in ordered)
