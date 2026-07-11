"""AutoML experiment endpoints: create, list, inspect experiments and runs."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import ExperimentServiceDep, require_permissions
from app.models.user import User
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentDetail,
    ExperimentRead,
    RunDetail,
    RunExplanation,
    RunRead,
)
from app.schemas.pagination import Page, PageParams

router = APIRouter(tags=["experiments"])

ExperimentReader = Annotated[User, Depends(require_permissions("experiment:read"))]
ExperimentCreator = Annotated[User, Depends(require_permissions("experiment:create"))]

Pagination = Annotated[PageParams, Query()]


@router.post(
    "/projects/{project_id}/experiments",
    response_model=ExperimentDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create and launch an experiment",
)
async def create_experiment(
    project_id: uuid.UUID,
    payload: ExperimentCreate,
    actor: ExperimentCreator,
    service: ExperimentServiceDep,
) -> ExperimentDetail:
    """Configure an AutoML experiment and launch its training."""
    experiment = await service.create(actor, project_id, payload)
    return ExperimentDetail.model_validate(experiment)


@router.get(
    "/projects/{project_id}/experiments",
    response_model=Page[ExperimentRead],
    summary="List experiments in a project",
)
async def list_experiments(
    project_id: uuid.UUID,
    actor: ExperimentReader,
    service: ExperimentServiceDep,
    params: Pagination,
) -> Page[ExperimentRead]:
    """Return a paginated list of experiments in a project."""
    items, total = await service.list(actor, project_id, params)
    return Page.create(
        items=[ExperimentRead.model_validate(e) for e in items],
        total=total,
        params=params,
    )


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentDetail,
    summary="Get an experiment",
)
async def get_experiment(
    experiment_id: uuid.UUID,
    actor: ExperimentReader,
    service: ExperimentServiceDep,
) -> ExperimentDetail:
    """Return an experiment with its runs and status."""
    experiment = await service.get(actor, experiment_id)
    return ExperimentDetail.model_validate(experiment)


@router.get(
    "/experiments/{experiment_id}/runs",
    response_model=list[RunRead],
    summary="List experiment runs",
)
async def list_runs(
    experiment_id: uuid.UUID,
    actor: ExperimentReader,
    service: ExperimentServiceDep,
) -> list[RunRead]:
    """Return the runs of an experiment, best-scoring first."""
    experiment = await service.get(actor, experiment_id)
    runs = sorted(
        experiment.runs,
        key=lambda run: (run.primary_score is not None, run.primary_score or 0.0),
        reverse=True,
    )
    return [RunRead.model_validate(run) for run in runs]


@router.get(
    "/experiments/{experiment_id}/runs/{run_id}",
    response_model=RunDetail,
    summary="Get a run with evaluation figures",
)
async def get_run(
    experiment_id: uuid.UUID,
    run_id: uuid.UUID,
    actor: ExperimentReader,
    service: ExperimentServiceDep,
) -> RunDetail:
    """Return a single run including its evaluation figures."""
    run = await service.get_run(actor, experiment_id, run_id)
    return RunDetail.model_validate(run)


@router.get(
    "/experiments/{experiment_id}/runs/{run_id}/explain",
    response_model=RunExplanation,
    summary="Explain a run (permutation & SHAP importance)",
)
async def explain_run(
    experiment_id: uuid.UUID,
    run_id: uuid.UUID,
    actor: ExperimentReader,
    service: ExperimentServiceDep,
) -> RunExplanation:
    """Return permutation feature importance and, when available, SHAP values."""
    explanation = await service.explain_run(actor, experiment_id, run_id)
    return RunExplanation.model_validate(explanation)
