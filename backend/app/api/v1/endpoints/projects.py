"""Project (workspace) CRUD endpoints.

Each route is guarded by a fine-grained permission. The guard dependency both
authorizes the request and yields the authenticated user, which is then passed to
the service so ownership rules are enforced in one place.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ProjectServiceDep, require_permissions
from app.models.user import User
from app.schemas.pagination import Page, PageParams
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])

# Permission-guarded principals for each action.
ProjectReader = Annotated[User, Depends(require_permissions("project:read"))]
ProjectCreator = Annotated[User, Depends(require_permissions("project:create"))]
ProjectEditor = Annotated[User, Depends(require_permissions("project:update"))]
ProjectDeleter = Annotated[User, Depends(require_permissions("project:delete"))]

Pagination = Annotated[PageParams, Query()]


@router.get("", response_model=Page[ProjectRead], summary="List projects")
async def list_projects(
    actor: ProjectReader,
    service: ProjectServiceDep,
    params: Pagination,
) -> Page[ProjectRead]:
    """Return a paginated list of projects visible to the caller."""
    items, total = await service.list(actor, params)
    return Page.create(
        items=[ProjectRead.model_validate(p) for p in items],
        total=total,
        params=params,
    )


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate,
    actor: ProjectCreator,
    service: ProjectServiceDep,
) -> ProjectRead:
    """Create a new project owned by the caller."""
    project = await service.create(actor, payload)
    return ProjectRead.model_validate(project)


@router.get("/{project_id}", response_model=ProjectRead, summary="Get a project")
async def get_project(
    project_id: uuid.UUID,
    actor: ProjectReader,
    service: ProjectServiceDep,
) -> ProjectRead:
    """Return a single project by id."""
    project = await service.get(actor, project_id)
    return ProjectRead.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectRead, summary="Update a project")
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    actor: ProjectEditor,
    service: ProjectServiceDep,
) -> ProjectRead:
    """Apply a partial update to a project."""
    project = await service.update(actor, project_id, payload)
    return ProjectRead.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
)
async def delete_project(
    project_id: uuid.UUID,
    actor: ProjectDeleter,
    service: ProjectServiceDep,
) -> None:
    """Soft-delete a project owned by the caller."""
    await service.delete(actor, project_id)
