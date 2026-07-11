"""Model-registry use-cases.

Promotes completed runs into a versioned registry and manages the deployment
lifecycle. Deploying a model to production atomically archives the previous
production model of the same name, so there is always exactly one live model per
name. All access is authorized through the owning project.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from app.core.constants import ModelStage, NotificationType, RunStatus
from app.core.exceptions import NotFoundError, UnprocessableEntityError
from app.core.logging import get_logger
from app.core.utils import slugify
from app.models.model import Model
from app.models.user import User
from app.repositories.experiment import ExperimentRepository, RunRepository
from app.repositories.model import ModelRepository
from app.schemas.model import ModelRegister
from app.schemas.pagination import PageParams
from app.services.notification import NotificationService
from app.services.project import ProjectService

logger = get_logger(__name__)


class ModelService:
    """Application service for the model registry."""

    def __init__(
        self,
        models: ModelRepository,
        runs: RunRepository,
        experiments: ExperimentRepository,
        projects: ProjectService,
        notifications: NotificationService,
    ) -> None:
        self._models = models
        self._runs = runs
        self._experiments = experiments
        self._projects = projects
        self._notifications = notifications

    # ------------------------------------------------------------------
    # Registration & lifecycle
    # ------------------------------------------------------------------
    async def register(self, actor: User, payload: ModelRegister) -> Model:
        """Promote a completed run into the registry as a new model version."""
        run = await self._runs.get(payload.run_id)
        if run is None:
            raise NotFoundError("Run not found.")
        experiment = await self._experiments.get(run.experiment_id)
        if experiment is None:
            raise NotFoundError("Experiment not found.")
        await self._projects.get(actor, experiment.project_id)  # authorize

        if run.status != RunStatus.COMPLETED or not run.artifact_key:
            raise UnprocessableEntityError("Only a completed, trained run can be registered.")

        slug = slugify(payload.name)
        version = await self._models.next_version(experiment.project_id, slug)
        model = await self._models.create(
            name=payload.name,
            slug=slug,
            version=version,
            description=payload.description,
            project_id=experiment.project_id,
            experiment_id=experiment.id,
            run_id=run.id,
            stage=ModelStage.NONE,
            algorithm=run.algorithm,
            task_type=experiment.task_type,
            target_column=experiment.target_column,
            primary_metric=experiment.primary_metric,
            primary_score=run.primary_score,
            metrics=run.metrics,
            feature_schema=run.feature_schema,
            class_names=run.class_names,
            artifact_key=run.artifact_key,
            created_by=actor.id,
        )
        logger.info("model_registered", model_id=str(model.id), version=version)

        if payload.deploy:
            model = await self._set_production(actor, model)
        return model

    async def deploy(self, actor: User, model_id: uuid.UUID) -> Model:
        """Deploy a model to production, archiving the prior production version."""
        model = await self.get(actor, model_id)
        return await self._set_production(actor, model)

    async def set_stage(self, actor: User, model_id: uuid.UUID, stage: ModelStage) -> Model:
        """Set a model's registry stage."""
        model = await self.get(actor, model_id)
        if stage == ModelStage.PRODUCTION:
            return await self._set_production(actor, model)
        return await self._models.update(model, stage=stage)

    async def _set_production(self, actor: User, model: Model) -> Model:
        """Make ``model`` the single production model for its name."""
        current = await self._models.get_production(model.project_id, model.slug)
        if current is not None and current.id != model.id:
            await self._models.update(current, stage=ModelStage.ARCHIVED)

        deployed = await self._models.update(model, stage=ModelStage.PRODUCTION)
        await self._notifications.create(
            actor.id,
            type=NotificationType.SUCCESS,
            title="Model deployed",
            message=f"{model.name} v{model.version} is now serving in production.",
            link=f"/models/{model.id}",
            meta={"model_id": str(model.id)},
        )
        logger.info("model_deployed", model_id=str(model.id))
        return deployed

    async def delete(self, actor: User, model_id: uuid.UUID) -> None:
        """Soft-delete a registered model."""
        model = await self.get(actor, model_id)
        await self._models.update(model, deleted_at=datetime.now(UTC))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    async def get(self, actor: User, model_id: uuid.UUID) -> Model:
        """Return a model the actor is authorized to access."""
        model = await self._models.get_active(model_id)
        if model is None:
            raise NotFoundError("Model not found.")
        await self._projects.get(actor, model.project_id)  # authorize
        return model

    async def list(
        self, actor: User, project_id: uuid.UUID, params: PageParams
    ) -> tuple[Sequence[Model], int]:
        """List models in a project the actor can access."""
        await self._projects.get(actor, project_id)
        return await self._models.list(params, filters={"project_id": project_id})

    async def compare(self, actor: User, model_ids: Sequence[uuid.UUID]) -> Sequence[Model]:
        """Return several models for side-by-side comparison.

        Annotated ``Sequence`` (not ``list``) because this class defines a
        ``list`` method that would otherwise shadow the builtin in annotations.
        """
        return [await self.get(actor, model_id) for model_id in model_ids]
