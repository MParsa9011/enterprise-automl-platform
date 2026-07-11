"""Experiment and run data-access repositories."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.experiment import Experiment, Run
from app.repositories.base import BaseRepository


class ExperimentRepository(BaseRepository[Experiment]):
    """Persistence operations for :class:`Experiment`."""

    model = Experiment
    searchable_fields = ("name", "description")

    async def get_with_runs(self, experiment_id: uuid.UUID) -> Experiment | None:
        """Return an experiment by id (runs are eagerly loaded via the model)."""
        return await self.session.get(Experiment, experiment_id)


class RunRepository(BaseRepository[Run]):
    """Persistence operations for :class:`Run`."""

    model = Run

    async def list_for_experiment(self, experiment_id: uuid.UUID) -> Sequence[Run]:
        """Return all runs of an experiment, best (highest score) first."""
        stmt = (
            select(Run)
            .where(Run.experiment_id == experiment_id)
            .order_by(Run.primary_score.desc().nullslast())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def best_for_experiment(self, experiment_id: uuid.UUID) -> Run | None:
        """Return the highest-scoring completed run of an experiment."""
        from app.core.constants import RunStatus

        stmt = (
            select(Run)
            .where(
                Run.experiment_id == experiment_id,
                Run.status == RunStatus.COMPLETED,
                Run.primary_score.is_not(None),
            )
            .order_by(Run.primary_score.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
