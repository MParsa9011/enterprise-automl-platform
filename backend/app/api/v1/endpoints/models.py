"""Model-registry and prediction endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    ModelServiceDep,
    PredictionServiceDep,
    require_permissions,
)
from app.models.user import User
from app.schemas.model import (
    ModelComparison,
    ModelRead,
    ModelRegister,
    ModelStageUpdate,
)
from app.schemas.pagination import Page, PageParams
from app.schemas.prediction import PredictionRequest, PredictionResponse

router = APIRouter(tags=["models"])

ModelReader = Annotated[User, Depends(require_permissions("model:read"))]
ModelDeployer = Annotated[User, Depends(require_permissions("model:deploy"))]
ModelDeleter = Annotated[User, Depends(require_permissions("model:delete"))]
Predictor = Annotated[User, Depends(require_permissions("prediction:create"))]

Pagination = Annotated[PageParams, Query()]

# Metrics surfaced in a comparison table.
_COMPARE_METRICS = ["accuracy", "f1_weighted", "roc_auc", "r2", "rmse", "mae"]


@router.post(
    "/models",
    response_model=ModelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a run as a model",
)
async def register_model(
    payload: ModelRegister,
    actor: ModelDeployer,
    service: ModelServiceDep,
) -> ModelRead:
    """Promote a completed training run into the versioned model registry."""
    model = await service.register(actor, payload)
    return ModelRead.model_validate(model)


@router.get(
    "/projects/{project_id}/models",
    response_model=Page[ModelRead],
    summary="List models in a project",
)
async def list_models(
    project_id: uuid.UUID,
    actor: ModelReader,
    service: ModelServiceDep,
    params: Pagination,
) -> Page[ModelRead]:
    """Return a paginated list of registered models in a project."""
    items, total = await service.list(actor, project_id, params)
    return Page.create(
        items=[ModelRead.model_validate(m) for m in items],
        total=total,
        params=params,
    )


@router.get("/models/compare", response_model=ModelComparison, summary="Compare models")
async def compare_models(
    actor: ModelReader,
    service: ModelServiceDep,
    model_ids: Annotated[list[uuid.UUID], Query(min_length=2, max_length=10)],
) -> ModelComparison:
    """Return several models side by side for metric comparison."""
    models = await service.compare(actor, model_ids)
    return ModelComparison(
        models=[ModelRead.model_validate(m) for m in models],
        metrics=_COMPARE_METRICS,
    )


@router.get("/models/{model_id}", response_model=ModelRead, summary="Get a model")
async def get_model(
    model_id: uuid.UUID,
    actor: ModelReader,
    service: ModelServiceDep,
) -> ModelRead:
    """Return a registered model by id."""
    return ModelRead.model_validate(await service.get(actor, model_id))


@router.post("/models/{model_id}/deploy", response_model=ModelRead, summary="Deploy a model")
async def deploy_model(
    model_id: uuid.UUID,
    actor: ModelDeployer,
    service: ModelServiceDep,
) -> ModelRead:
    """Promote a model to production, archiving the prior production version."""
    return ModelRead.model_validate(await service.deploy(actor, model_id))


@router.patch("/models/{model_id}/stage", response_model=ModelRead, summary="Set model stage")
async def set_model_stage(
    model_id: uuid.UUID,
    payload: ModelStageUpdate,
    actor: ModelDeployer,
    service: ModelServiceDep,
) -> ModelRead:
    """Set a model's registry stage (staging/production/archived/none)."""
    return ModelRead.model_validate(await service.set_stage(actor, model_id, payload.stage))


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a model",
)
async def delete_model(
    model_id: uuid.UUID,
    actor: ModelDeleter,
    service: ModelServiceDep,
) -> None:
    """Soft-delete a registered model."""
    await service.delete(actor, model_id)


@router.post(
    "/models/{model_id}/predict",
    response_model=PredictionResponse,
    summary="Predict with a model",
)
async def predict(
    model_id: uuid.UUID,
    payload: PredictionRequest,
    actor: Predictor,
    service: PredictionServiceDep,
) -> PredictionResponse:
    """Run predictions for a batch of JSON records against a registered model."""
    return await service.predict(actor, model_id, payload.records)
