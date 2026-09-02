"""L3 — rival behavioural profiling.

Every feature here is computed from a rival's public transfer, chip and points
history. The LLM's only job in this layer is putting a human label on an
archetype that has already been *chosen by rules* from a fixed enum — it never
invents a feature and never picks an archetype that the numbers do not support.

This is also the compounding asset. A competitor arriving next season can read
the same public API, but they cannot retroactively acquire a season of observed
behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from overtake.core.config import settings
from overtake.models import (
    ManagerChip,
    ManagerHistory,
    ManagerPick,
    ManagerTransfer,
    Player,
    RivalProfile,
)

ARCHETYPE_LABELS = {
    "template_loyalist": "Template loyalist",
    "hit_taker": "Hit-taker",
    "set_and_forget": "Set-and-forget",
    "chaser": "Chaser",
    "early_wildcarder": "Early wildcarder",
    "differential_hunter": "Differential hunter",
    "steady_operator": "Steady operator",
    "unknown": "Not enough history yet",
}

ARCHETYPE_BLURBS = {
    "template_loyalist": "Owns what everyone owns. Hard to gain on, hard to lose to.",
    "hit_taker": "Takes points hits regularly. Volatile — that cuts both ways.",
    "set_and_forget": "Rarely transfers. Their squad drifts as the season moves on.",
    "chaser": "Buys last week's top scorer. Consistently a week late.",
    "early_wildcarder": "Spends chips early. Fewer levers left than you have.",
    "differential_hunter": "Deliberately owns what the field does not.",
    "steady_operator": "One transfer a week, no drama. The hardest kind to catch.",
    "unknown": "Too few gameweeks observed to call it yet.",
}

MIN_GAMEWEEKS_FOR_ARCHETYPE = 5
"""Below this, the honest answer is 'we do not know yet'."""

# Population priors. Every feature is shrunk toward these, because two
# gameweeks of history is noise, not personality: an early version of this
# module read one transfer as "chases last week's points, always" and fed a
# 1.00 reactivity straight into the simulation.
PRIOR_HIT_RATE = 0.15
PRIOR_TRANSFERS_PER_GW = 1.0
PRIOR_TEMPLATE_SCORE = 0.5
PRIOR_REACTIVITY = 0.30
PRIOR_INACTIVITY = 0.15
PRIOR_BENCH_WASTE = 4.0
SHRINK_GAMEWEEKS = 6.0
"""Half weight on observed behaviour after six gameweeks of evidence."""
SHRINK_TRANSFERS = 5.0


def _shrink(observed: float, prior: float, n: float, strength: float) -> float:
    """Blend an observed rate with a population prior by sample size."""
    if n <= 0:
        return prior
    weight = n / (n + strength)
    return weight * observed + (1 - weight) * prior


@dataclass
class ProfileFeatures:
    entry_id: int
    hit_rate: float
    transfers_per_gw: float
    template_score: float
    reactivity: float
    bench_waste: float
    inactivity: float
    gameweeks_observed: int
    chips_used: dict[str, int]

    def archetype(self) -> str:
        """Rule-based, ordered by how strongly each signal identifies a manager."""
        if self.gameweeks_observed < MIN_GAMEWEEKS_FOR_ARCHETYPE:
            return "unknown"
        if self.inactivity >= 0.5 or self.transfers_per_gw < 0.25:
            return "set_and_forget"
        if self.hit_rate >= 0.4:
            return "hit_taker"
        if self.chips_used and min(self.chips_used.values()) <= 6:
            return "early_wildcarder"
        if self.reactivity >= 0.5:
            return "chaser"
        if self.template_score >= 0.7:
            return "template_loyalist"
        if self.template_score <= 0.35:
            return "differential_hunter"
        return "steady_operator"

    def as_row(self) -> dict[str, Any]:
        archetype = self.archetype()
        return {
            "entry_id": self.entry_id,
            "season": settings.season,
            "archetype": archetype,
            "archetype_label": ARCHETYPE_LABELS[archetype],
            "hit_rate": round(self.hit_rate, 3),
            "template_score": round(self.template_score, 3),
            "reactivity": round(self.reactivity, 3),
            "bench_waste": round(self.bench_waste, 2),
            "inactivity": round(self.inactivity, 3),
            "transfers_per_gw": round(self.transfers_per_gw, 3),
            "gameweeks_observed": self.gameweeks_observed,
            "chips_used": self.chips_used,
            "computed_at": datetime.now(UTC),
        }


class ProfilingEngine:
    """Computes behavioural features for every manager in a league."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _ownership(self, gameweek: int, entry_ids: list[int]) -> dict[int, float]:
        """Share of the league owning each player in the given gameweek.

        The league's own template is the right reference point: a manager is a
        'template loyalist' relative to the people they are actually playing
        against, not relative to thirteen million strangers.
        """
        picks = (
            (
                await self.session.execute(
                    select(ManagerPick).where(
                        ManagerPick.gameweek_id == gameweek,
                        ManagerPick.entry_id.in_(entry_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        if not picks:
            return {}
        counts: dict[int, int] = {}
        for row in picks:
            for pick in row.picks:
                counts[pick["element"]] = counts.get(pick["element"], 0) + 1
        return {pid: count / len(picks) for pid, count in counts.items()}

    async def compute(self, entry_ids: list[int], current_gameweek: int) -> list[ProfileFeatures]:
        if not entry_ids:
            return []

        history = (
            (
                await self.session.execute(
                    select(ManagerHistory).where(ManagerHistory.entry_id.in_(entry_ids))
                )
            )
            .scalars()
            .all()
        )
        transfers = (
            (
                await self.session.execute(
                    select(ManagerTransfer).where(ManagerTransfer.entry_id.in_(entry_ids))
                )
            )
            .scalars()
            .all()
        )
        chips = (
            (
                await self.session.execute(
                    select(ManagerChip).where(ManagerChip.entry_id.in_(entry_ids))
                )
            )
            .scalars()
            .all()
        )
        picks = (
            (
                await self.session.execute(
                    select(ManagerPick).where(ManagerPick.entry_id.in_(entry_ids))
                )
            )
            .scalars()
            .all()
        )
        ownership = await self._ownership(current_gameweek, entry_ids)
        top_scorers = await self._recent_top_scorers(current_gameweek)

        by_entry_history: dict[int, list[ManagerHistory]] = {}
        for h in history:
            by_entry_history.setdefault(h.entry_id, []).append(h)
        by_entry_transfers: dict[int, list[ManagerTransfer]] = {}
        for t in transfers:
            by_entry_transfers.setdefault(t.entry_id, []).append(t)
        by_entry_chips: dict[int, dict[str, int]] = {}
        for c in chips:
            by_entry_chips.setdefault(c.entry_id, {})[c.name] = c.gameweek_id
        latest_picks: dict[int, ManagerPick] = {}
        for p in picks:
            existing = latest_picks.get(p.entry_id)
            if existing is None or p.gameweek_id > existing.gameweek_id:
                latest_picks[p.entry_id] = p

        out: list[ProfileFeatures] = []
        for entry_id in entry_ids:
            rows = sorted(by_entry_history.get(entry_id, []), key=lambda r: r.gameweek_id)
            observed = len(rows)
            if observed == 0:
                out.append(
                    ProfileFeatures(
                        entry_id=entry_id,
                        hit_rate=PRIOR_HIT_RATE,
                        transfers_per_gw=PRIOR_TRANSFERS_PER_GW,
                        template_score=PRIOR_TEMPLATE_SCORE,
                        reactivity=PRIOR_REACTIVITY,
                        bench_waste=PRIOR_BENCH_WASTE,
                        inactivity=PRIOR_INACTIVITY,
                        gameweeks_observed=0,
                        chips_used={},
                    )
                )
                continue

            # Gameweek 1 carries no transfer information: nobody can transfer
            # before their first squad exists, so including it would make every
            # manager look inactive.
            transferable = [r for r in rows if r.gameweek_id > 1]
            n_transferable = float(len(transferable))

            hits = sum(1 for r in transferable if r.event_transfers_cost > 0)
            total_transfers = sum(r.event_transfers for r in transferable)
            idle = sum(1 for r in transferable if r.event_transfers == 0)
            bench = sum(r.points_on_bench for r in rows) / observed

            entry_transfers = by_entry_transfers.get(entry_id, [])
            reactivity = self._reactivity(entry_transfers, top_scorers)

            pick_row = latest_picks.get(entry_id)
            template = self._template_score(pick_row, ownership)

            out.append(
                ProfileFeatures(
                    entry_id=entry_id,
                    hit_rate=_shrink(
                        hits / n_transferable if n_transferable else 0.0,
                        PRIOR_HIT_RATE,
                        n_transferable,
                        SHRINK_GAMEWEEKS,
                    ),
                    transfers_per_gw=_shrink(
                        total_transfers / n_transferable if n_transferable else 0.0,
                        PRIOR_TRANSFERS_PER_GW,
                        n_transferable,
                        SHRINK_GAMEWEEKS,
                    ),
                    template_score=template,
                    reactivity=reactivity,
                    bench_waste=_shrink(
                        bench, PRIOR_BENCH_WASTE, float(observed), SHRINK_GAMEWEEKS
                    ),
                    inactivity=_shrink(
                        idle / n_transferable if n_transferable else 0.0,
                        PRIOR_INACTIVITY,
                        n_transferable,
                        SHRINK_GAMEWEEKS,
                    ),
                    gameweeks_observed=observed,
                    chips_used=by_entry_chips.get(entry_id, {}),
                )
            )
        return out

    async def _recent_top_scorers(self, current_gameweek: int) -> dict[int, set[int]]:
        """gameweek -> the 20 highest-scoring players that gameweek."""
        from overtake.models import PlayerGameweekStat

        rows = (
            (
                await self.session.execute(
                    select(PlayerGameweekStat).where(
                        PlayerGameweekStat.gameweek_id < current_gameweek
                    )
                )
            )
            .scalars()
            .all()
        )
        by_gw: dict[int, list[tuple[int, int]]] = {}
        for r in rows:
            by_gw.setdefault(r.gameweek_id, []).append((r.total_points, r.player_id))
        return {
            gw: {pid for _pts, pid in sorted(items, reverse=True)[:20]}
            for gw, items in by_gw.items()
        }

    @staticmethod
    def _reactivity(transfers: list[ManagerTransfer], top_scorers: dict[int, set[int]]) -> float:
        """Share of transfers-in that were a top scorer the week before.

        This is the 'chaser' signal: buying last week's points is the single
        most common and most costly pattern in the game.
        """
        considered = [t for t in transfers if (t.gameweek_id - 1) in top_scorers]
        if not considered:
            return PRIOR_REACTIVITY
        chased = sum(1 for t in considered if t.element_in in top_scorers[t.gameweek_id - 1])
        return _shrink(
            chased / len(considered), PRIOR_REACTIVITY, float(len(considered)), SHRINK_TRANSFERS
        )

    @staticmethod
    def _template_score(pick_row: ManagerPick | None, ownership: dict[int, float]) -> float:
        """Mean league-ownership of the players this manager owns.

        1.0 means they own exactly what everyone owns; near 0 means they have
        gone their own way entirely.
        """
        if pick_row is None or not ownership:
            return PRIOR_TEMPLATE_SCORE
        owned = [ownership.get(p["element"], 0.0) for p in pick_row.picks]
        if not owned:
            return PRIOR_TEMPLATE_SCORE
        # A single gameweek of picks is a real observation (unlike a transfer
        # rate), so this needs far less shrinkage — but a manager's squad still
        # moves, so it is not taken at face value either.
        return _shrink(sum(owned) / len(owned), PRIOR_TEMPLATE_SCORE, 4.0, 1.0)

    async def compute_and_store(
        self, entry_ids: list[int], current_gameweek: int
    ) -> list[ProfileFeatures]:
        from overtake.fpl.ingest import _bulk_upsert

        features = await self.compute(entry_ids, current_gameweek)
        rows = [f.as_row() for f in features]
        await _bulk_upsert(self.session, RivalProfile, rows, ["entry_id", "season"])
        return features

    async def load(self, entry_ids: list[int]) -> dict[int, RivalProfile]:
        rows = (
            (
                await self.session.execute(
                    select(RivalProfile).where(
                        RivalProfile.entry_id.in_(entry_ids),
                        RivalProfile.season == settings.season,
                    )
                )
            )
            .scalars()
            .all()
        )
        return {r.entry_id: r for r in rows}


async def player_name_map(session: AsyncSession, player_ids: list[int]) -> dict[int, str]:
    if not player_ids:
        return {}
    rows = (
        await session.execute(select(Player.id, Player.web_name).where(Player.id.in_(player_ids)))
    ).all()
    return dict(rows)  # type: ignore[arg-type]  # SQLAlchemy Row is a tuple at runtime
