"""AutoML experiment use-cases and training orchestration.

``create`` validates and persists an experiment; ``launch`` dispatches it (inline
in tests, to Celery in production); ``run_experiment`` is the system-level
orchestration that trains every requested algorithm, records a :class:`Run` per
algorithm and marks the best-scoring run on the experiment. Orchestration is
written once, in async, so the same code path serves both the inline and the
Celery execution modes.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from functools import partial

import anyio

from app.core.config import settings
from app.core.constants import (
    DatasetFileType,
    ExperimentStatus,
    RunStatus,
    TaskType,
)
from app.core.exceptions import NotFoundError, UnprocessableEntityError
from app.core.logging import get_logger
from app.ml.algorithms import available_keys, get_algorithm
from app.ml.evaluation import DEFAULT_PRIMARY_METRIC, PRIMARY_METRICS
from app.ml.io import read_tabular
from app.ml.training import TrainingError, train_algorithm
from app.models.experiment import Experiment, Run
from app.models.user import User
from app.repositories.dataset import DatasetVersionRepository
from app.repositories.experiment import ExperimentRepository, RunRepository
from app.core.constants import NotificationType
from app.schemas.experiment import ExperimentCreate
from app.schemas.pagination import PageParams
from app.services.dataset import DatasetService
from app.services.notification import NotificationService
from app.services.project import ProjectService
from app.storage.base import Storage

logger = get_logger(__name__)


class ExperimentService:
    """Application service for AutoML experiments."""

    def __init__(
        self,
        experiments: ExperimentRepository,
        runs: RunRepository,
        dataset_versions: DatasetVersionRepository,
        datasets: DatasetService,
        projects: ProjectService,
        storage: Storage,
        notifications: NotificationService,
    ) -> None:
        self._experiments = experiments
        self._runs = runs
        self._dataset_versions = dataset_versions
        self._datasets = datasets
        self._projects = projects
        self._storage = storage
        self._notifications = notifications

    # ------------------------------------------------------------------
    # Create & launch
    # ------------------------------------------------------------------
    async def create(
        self, actor: User, project_id: uuid.UUID, payload: ExperimentCreate
    ) -> Experiment:
        """Validate and persist an experiment, then launch its training."""
        dataset = await self._datasets.get(actor, payload.dataset_id)
        if dataset.project_id != project_id:
            raise NotFoundError("Dataset not found in this project.")

        version = payload.dataset_version or dataset.latest_version
        await self._datasets.get_version(actor, dataset.id, version)

        if payload.task_type == TaskType.CLUSTERING:
            raise UnprocessableEntityError("Clustering experiments are not yet supported.")

        primary_metric = self._resolve_primary_metric(payload)
        algorithms = self._resolve_algorithms(payload)

        experiment = await self._experiments.create(
            name=payload.name,
            description=payload.description,
            project_id=project_id,
            dataset_id=dataset.id,
            dataset_version=version,
            task_type=payload.task_type,
            target_column=payload.target_column,
            feature_config=payload.feature_config.model_dump(),
            algorithms=algorithms,
            primary_metric=primary_metric,
            optimize=payload.optimize,
            n_trials=payload.n_trials,
            cv_folds=payload.cv_folds,
            test_size=payload.test_size,
            status=ExperimentStatus.QUEUED,
            created_by=actor.id,
        )
        logger.info("experiment_created", experiment_id=str(experiment.id))
        await self._launch(experiment.id)
        return experiment

    async def _launch(self, experiment_id: uuid.UUID) -> None:
        """Dispatch training inline (tests) or to a Celery worker (production)."""
        if settings.RUN_TRAINING_INLINE:
            await self.run_experiment(experiment_id)
        else:  # pragma: no cover - exercised in a real deployment
            from app.worker.celery_app import celery_app

            celery_app.send_task("app.worker.tasks.train_experiment", args=[str(experiment_id)])

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    async def run_experiment(self, experiment_id: uuid.UUID) -> None:
        """Train every requested algorithm and record the best run."""
        experiment = await self._experiments.get(experiment_id)
        if experiment is None or experiment.status not in (
            ExperimentStatus.QUEUED,
            ExperimentStatus.DRAFT,
        ):
            return

        await self._experiments.update(experiment, status=ExperimentStatus.RUNNING)
        try:
            frame = await self._load_dataframe(experiment)
        except Exception as exc:  # noqa: BLE001 - surface any load error on the experiment
            logger.exception("experiment_load_failed", experiment_id=str(experiment_id))
            await self._experiments.update(
                experiment, status=ExperimentStatus.FAILED, error_message=str(exc)
            )
            return

        best_run_id: uuid.UUID | None = None
        best_score: float | None = None

        for algorithm_key in experiment.algorithms:
            run = await self._train_one(experiment, algorithm_key, frame)
            if run.status == RunStatus.COMPLETED and run.primary_score is not None:
                if best_score is None or run.primary_score > best_score:
                    best_score, best_run_id = run.primary_score, run.id

        completed = best_run_id is not None
        await self._experiments.update(
            experiment,
            status=ExperimentStatus.COMPLETED if completed else ExperimentStatus.FAILED,
            best_run_id=best_run_id,
            error_message=None if completed else "All training runs failed.",
        )
        await self._notify_finished(experiment, completed)
        logger.info(
            "experiment_finished",
            experiment_id=str(experiment_id),
            best_run_id=str(best_run_id) if best_run_id else None,
        )

    async def _notify_finished(self, experiment: Experiment, completed: bool) -> None:
        """Notify the experiment's owner that training has finished."""
        if experiment.created_by is None:
            return
        await self._notifications.create(
            experiment.created_by,
            type=NotificationType.SUCCESS if completed else NotificationType.ERROR,
            title="Experiment finished" if completed else "Experiment failed",
            message=(
                f"'{experiment.name}' completed training."
                if completed
                else f"'{experiment.name}' failed to produce a model."
            ),
            link=f"/experiments/{experiment.id}",
            meta={"experiment_id": str(experiment.id)},
        )

    async def _train_one(self, experiment: Experiment, algorithm_key: str, frame: object) -> Run:
        """Train a single algorithm and persist its run outcome."""
        run = await self._runs.create(
            experiment_id=experiment.id,
            algorithm=algorithm_key,
            status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        try:
            spec = get_algorithm(algorithm_key)
        except KeyError as exc:
            return await self._fail_run(run, str(exc))

        try:
            from app.ml.features import FeatureConfig, ImputationConfig

            config_data = dict(experiment.feature_config or {})
            imputation = ImputationConfig(**config_data.pop("imputation", {}))
            feature_config = FeatureConfig(imputation=imputation, **config_data)

            result = await anyio.to_thread.run_sync(
                partial(
                    train_algorithm,
                    frame,
                    task_type=TaskType(experiment.task_type),
                    target=experiment.target_column or "",
                    feature_config=feature_config,
                    algorithm=spec,
                    primary_metric=experiment.primary_metric,
                    optimize=experiment.optimize,
                    n_trials=experiment.n_trials,
                    cv_folds=experiment.cv_folds,
                    test_size=experiment.test_size,
                    random_state=experiment.random_state,
                )
            )
        except (TrainingError, ValueError) as exc:
            return await self._fail_run(run, str(exc))
        except Exception as exc:  # noqa: BLE001 - one algorithm failing must not abort the rest
            logger.exception("run_failed", run_id=str(run.id), algorithm=algorithm_key)
            return await self._fail_run(run, str(exc))

        artifact_key = f"models/{experiment.project_id}/{experiment.id}/{run.id}.joblib"
        await self._storage.save(artifact_key, result.artifact)

        # Best-effort MLflow logging (no-op unless explicitly enabled).
        from app.ml.tracking import log_run

        await anyio.to_thread.run_sync(
            partial(
                log_run,
                experiment_name=experiment.name,
                run_name=f"{algorithm_key}-{run.id}",
                algorithm=algorithm_key,
                params=result.params,
                metrics=result.metrics,
            )
        )

        return await self._runs.update(
            run,
            status=RunStatus.COMPLETED,
            metrics=result.metrics,
            figures=result.figures,
            params=result.params,
            primary_score=result.primary_score,
            feature_schema=result.feature_schema,
            class_names=result.class_names,
            artifact_key=artifact_key,
            duration_seconds=result.duration_seconds,
            finished_at=datetime.now(UTC),
        )

    async def _fail_run(self, run: Run, message: str) -> Run:
        """Mark a run as failed with an error message."""
        return await self._runs.update(
            run,
            status=RunStatus.FAILED,
            error_message=message[:2000],
            finished_at=datetime.now(UTC),
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def list(
        self, actor: User, project_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[Experiment], int]:
        """List experiments in a project the actor can access."""
        await self._projects.get(actor, project_id)  # authorize project access
        return await self._experiments.list(params, filters={"project_id": project_id})

    async def get(self, actor: User, experiment_id: uuid.UUID) -> Experiment:
        """Return an experiment the actor is authorized to access."""
        experiment = await self._experiments.get(experiment_id)
        if experiment is None:
            raise NotFoundError("Experiment not found.")
        await self._projects.get(actor, experiment.project_id)  # authorize
        return experiment

    async def get_run(self, actor: User, experiment_id: uuid.UUID, run_id: uuid.UUID) -> Run:
        """Return a specific run of an experiment."""
        await self.get(actor, experiment_id)
        run = await self._runs.get(run_id)
        if run is None or run.experiment_id != experiment_id:
            raise NotFoundError("Run not found.")
        return run

    async def explain_run(
        self, actor: User, experiment_id: uuid.UUID, run_id: uuid.UUID
    ) -> dict[str, object]:
        """Compute permutation (and, when available, SHAP) importances for a run."""
        from app.ml.explain import explain
        from app.ml.training import load_model, sklearn_scoring

        experiment = await self.get(actor, experiment_id)
        run = await self.get_run(actor, experiment_id, run_id)
        if run.status != RunStatus.COMPLETED or not run.artifact_key:
            raise UnprocessableEntityError("Run has no trained model to explain.")

        artifact = await self._storage.read(run.artifact_key)
        frame = await self._load_dataframe(experiment)
        model = await anyio.to_thread.run_sync(load_model, artifact)
        scoring = sklearn_scoring(experiment.primary_metric, len(run.class_names or []))

        return await anyio.to_thread.run_sync(
            partial(
                explain,
                model,
                frame,
                task_type=TaskType(experiment.task_type),
                target=experiment.target_column or "",
                class_names=run.class_names,
                scoring=scoring,
                random_state=experiment.random_state,
            )
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _load_dataframe(self, experiment: Experiment) -> object:
        """Load and parse the experiment's dataset version into a dataframe."""
        version = await self._dataset_versions.get_for_dataset(
            experiment.dataset_id, experiment.dataset_version
        )
        if version is None:
            raise NotFoundError("Dataset version not found.")
        content = await self._storage.read(version.storage_key)
        file_type = DatasetFileType(version.file_type)
        return await anyio.to_thread.run_sync(read_tabular, content, file_type)

    @staticmethod
    def _resolve_primary_metric(payload: ExperimentCreate) -> str:
        """Validate or default the primary metric for the task."""
        allowed = PRIMARY_METRICS[payload.task_type]
        if payload.primary_metric is None:
            return DEFAULT_PRIMARY_METRIC[payload.task_type]
        if payload.primary_metric not in allowed:
            raise UnprocessableEntityError(
                f"Invalid primary metric {payload.primary_metric!r}; choose from {allowed}."
            )
        return payload.primary_metric

    @staticmethod
    def _resolve_algorithms(payload: ExperimentCreate) -> list[str]:
        """Validate or default the algorithm set for the task."""
        supported = available_keys(payload.task_type)
        if not payload.algorithms:
            return supported
        unknown = [a for a in payload.algorithms if a not in supported]
        if unknown:
            raise UnprocessableEntityError(
                f"Unsupported algorithms for {payload.task_type}: {unknown}. "
                f"Available: {supported}."
            )
        return payload.algorithms
