"""Exploratory data analysis and feature-preview endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import EdaServiceDep, require_permissions
from app.models.user import User
from app.schemas.eda import EdaResponse
from app.schemas.features import FeatureConfigIn, FeaturePreviewResponse

router = APIRouter(tags=["eda"])

DatasetReader = Annotated[User, Depends(require_permissions("dataset:read"))]


@router.get(
    "/datasets/{dataset_id}/versions/{version}/eda",
    response_model=EdaResponse,
    summary="Generate automated EDA",
)
async def get_eda(
    dataset_id: uuid.UUID,
    version: int,
    actor: DatasetReader,
    service: EdaServiceDep,
) -> EdaResponse:
    """Return automated EDA figures (missing values, distributions, correlations)."""
    figures = await service.generate(actor, dataset_id, version)
    return EdaResponse(dataset_id=dataset_id, version=version, **figures)


@router.post(
    "/datasets/{dataset_id}/versions/{version}/feature-preview",
    response_model=FeaturePreviewResponse,
    summary="Preview a feature-engineering pipeline",
)
async def preview_features(
    dataset_id: uuid.UUID,
    version: int,
    payload: FeatureConfigIn,
    actor: DatasetReader,
    service: EdaServiceDep,
) -> FeaturePreviewResponse:
    """Fit the configured preprocessing pipeline and summarise the transformed output."""
    result = await service.preview_features(actor, dataset_id, version, payload.to_config())
    return FeaturePreviewResponse.model_validate(result)
