"""Celery tasks.

Training tasks build their own async session and service graph, then drive the
shared :meth:`ExperimentService.run_experiment` orchestration inside a fresh event
loop. Reusing the async orchestration keeps a single code path across inline (test)
and worker (production) execution.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.services.experiment import ExperimentService
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


def _build_service(session: AsyncSession) -> ExperimentService:
    """Assemble an :class:`ExperimentService` bound to ``session``."""
    from app.repositories.dataset import DatasetRepository, DatasetVersionRepository
    from app.repositories.experiment import ExperimentRepository, RunRepository
    from app.repositories.project import ProjectRepository
    from app.services.dataset import DatasetService
    from app.services.project import ProjectService
    from app.storage import LocalStorage
    from app.core.config import settings

    projects = ProjectService(ProjectRepository(session))
    storage = LocalStorage(settings.STORAGE_ROOT)
    datasets = DatasetService(
        DatasetRepository(session),
        DatasetVersionRepository(session),
        storage,
        projects,
    )
    return ExperimentService(
        ExperimentRepository(session),
        RunRepository(session),
        DatasetVersionRepository(session),
        datasets,
        projects,
        storage,
    )


async def _run(experiment_id: str) -> None:
    """Run an experiment within a fresh async session and commit."""
    from app.db.session import AsyncSessionFactory

    async with AsyncSessionFactory() as session:
        service = _build_service(session)
        await service.run_experiment(uuid.UUID(experiment_id))
        await session.commit()


@celery_app.task(name="app.worker.tasks.train_experiment", bind=True, max_retries=0)
def train_experiment(self, experiment_id: str) -> dict[str, str]:  # type: ignore[no-untyped-def]
    """Celery entrypoint: train all algorithms for an experiment."""
    logger.info("celery_train_experiment_started", experiment_id=experiment_id)
    asyncio.run(_run(experiment_id))
    logger.info("celery_train_experiment_finished", experiment_id=experiment_id)
    return {"experiment_id": experiment_id, "status": "finished"}
