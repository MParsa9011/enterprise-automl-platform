"""Dataset management endpoints: upload, versioning, statistics and download."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status

from app.api.deps import DatasetServiceDep, require_permissions
from app.models.user import User
from app.schemas.dataset import (
    DatasetDetail,
    DatasetRead,
    DatasetVersionDetail,
    DatasetVersionRead,
)
from app.schemas.pagination import Page, PageParams

router = APIRouter(tags=["datasets"])

DatasetReader = Annotated[User, Depends(require_permissions("dataset:read"))]
DatasetCreator = Annotated[User, Depends(require_permissions("dataset:create"))]
DatasetDeleter = Annotated[User, Depends(require_permissions("dataset:delete"))]

Pagination = Annotated[PageParams, Query()]


@router.post(
    "/projects/{project_id}/datasets",
    response_model=DatasetDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a dataset",
)
async def upload_dataset(
    project_id: uuid.UUID,
    actor: DatasetCreator,
    service: DatasetServiceDep,
    file: Annotated[UploadFile, File(description="CSV or Excel file")],
    name: Annotated[str, Form(min_length=1, max_length=150)],
    description: Annotated[str | None, Form(max_length=2000)] = None,
) -> DatasetDetail:
    """Create a dataset from an uploaded CSV/Excel file (becomes version 1)."""
    from app.schemas.dataset import DatasetCreate

    content = await file.read()
    dataset = await service.create(
        actor,
        project_id,
        DatasetCreate(name=name, description=description),
        filename=file.filename or "upload.csv",
        content=content,
    )
    return DatasetDetail.model_validate(dataset)


@router.get(
    "/projects/{project_id}/datasets",
    response_model=Page[DatasetRead],
    summary="List datasets in a project",
)
async def list_datasets(
    project_id: uuid.UUID,
    actor: DatasetReader,
    service: DatasetServiceDep,
    params: Pagination,
) -> Page[DatasetRead]:
    """Return a paginated list of datasets in a project."""
    items, total = await service.list(actor, project_id, params)
    return Page.create(
        items=[DatasetRead.model_validate(d) for d in items],
        total=total,
        params=params,
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail, summary="Get a dataset")
async def get_dataset(
    dataset_id: uuid.UUID,
    actor: DatasetReader,
    service: DatasetServiceDep,
) -> DatasetDetail:
    """Return a dataset and its version history."""
    dataset = await service.get(actor, dataset_id)
    return DatasetDetail.model_validate(dataset)


@router.post(
    "/datasets/{dataset_id}/versions",
    response_model=DatasetVersionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a dataset version",
)
async def add_version(
    dataset_id: uuid.UUID,
    actor: DatasetCreator,
    service: DatasetServiceDep,
    file: Annotated[UploadFile, File(description="CSV or Excel file")],
) -> DatasetVersionRead:
    """Upload a new file as the next immutable version of a dataset."""
    content = await file.read()
    version = await service.add_version(
        actor, dataset_id, filename=file.filename or "upload.csv", content=content
    )
    return DatasetVersionRead.model_validate(version)


@router.get(
    "/datasets/{dataset_id}/versions/{version}",
    response_model=DatasetVersionDetail,
    summary="Get version statistics",
)
async def get_version(
    dataset_id: uuid.UUID,
    version: int,
    actor: DatasetReader,
    service: DatasetServiceDep,
) -> DatasetVersionDetail:
    """Return a dataset version including its full statistical profile."""
    record = await service.get_version(actor, dataset_id, version)
    return DatasetVersionDetail.model_validate(record)


@router.get(
    "/datasets/{dataset_id}/versions/{version}/download",
    summary="Download the raw dataset file",
    response_class=Response,
)
async def download_version(
    dataset_id: uuid.UUID,
    version: int,
    actor: DatasetReader,
    service: DatasetServiceDep,
) -> Response:
    """Stream the original uploaded file for a dataset version."""
    record, content = await service.read_content(actor, dataset_id, version)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{record.original_filename}"'
        },
    )


@router.delete(
    "/datasets/{dataset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a dataset",
)
async def delete_dataset(
    dataset_id: uuid.UUID,
    actor: DatasetDeleter,
    service: DatasetServiceDep,
) -> None:
    """Soft-delete a dataset and hide it from listings."""
    await service.delete(actor, dataset_id)
