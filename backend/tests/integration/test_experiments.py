"""End-to-end integration tests for the AutoML experiment flow.

Experiments train inline (``RUN_TRAINING_INLINE`` is set in conftest), so a create
call returns only once every algorithm has been trained and evaluated. Fast
algorithms and small data keep these tests quick.
"""

from __future__ import annotations

import io
import random

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.ml]

AUTH = "/api/v1/auth"
PROJECTS = "/api/v1/projects"


def _classification_csv(n: int = 60) -> bytes:
    """Generate a separable binary-classification dataset as CSV."""
    rng = random.Random(42)
    rows = ["x1,x2,x3,target"]
    for _ in range(n):
        label = rng.randint(0, 1)
        # Two loosely separated Gaussian blobs.
        x1 = rng.gauss(2 if label else -2, 1.0)
        x2 = rng.gauss(1 if label else -1, 1.0)
        x3 = rng.gauss(0, 1.0)
        rows.append(f"{x1:.3f},{x2:.3f},{x3:.3f},{label}")
    return ("\n".join(rows) + "\n").encode()


async def _prepare(client: AsyncClient, email: str) -> tuple[dict[str, str], str, str]:
    """Register a user, create a project and upload a dataset."""
    reg = await client.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Passw0rd!", "full_name": "DS"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
    project_id = (await client.post(PROJECTS, json={"name": "P"}, headers=headers)).json()["id"]
    dataset = await client.post(
        f"{PROJECTS}/{project_id}/datasets",
        headers=headers,
        data={"name": "Blobs"},
        files={"file": ("blobs.csv", io.BytesIO(_classification_csv()), "text/csv")},
    )
    return headers, project_id, dataset.json()["id"]


class TestExperimentLifecycle:
    async def test_classification_experiment_trains_and_selects_best(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, dataset_id = await _prepare(client, unique_email)
        resp = await client.post(
            f"{PROJECTS}/{project_id}/experiments",
            headers=headers,
            json={
                "name": "Churn AutoML",
                "dataset_id": dataset_id,
                "task_type": "classification",
                "target_column": "target",
                "algorithms": ["logistic_regression", "decision_tree"],
                "optimize": False,
                "cv_folds": 2,
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "completed"
        assert body["best_run_id"] is not None
        assert len(body["runs"]) == 2
        assert all(r["status"] == "completed" for r in body["runs"])
        # The best run has an accuracy metric recorded.
        best = next(r for r in body["runs"] if r["id"] == body["best_run_id"])
        assert "accuracy" in best["metrics"]

    async def test_run_detail_includes_figures(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, dataset_id = await _prepare(client, unique_email)
        exp = await client.post(
            f"{PROJECTS}/{project_id}/experiments",
            headers=headers,
            json={
                "name": "Fig test",
                "dataset_id": dataset_id,
                "task_type": "classification",
                "target_column": "target",
                "algorithms": ["logistic_regression"],
                "cv_folds": 2,
            },
        )
        experiment = exp.json()
        run_id = experiment["runs"][0]["id"]
        detail = await client.get(
            f"/api/v1/experiments/{experiment['id']}/runs/{run_id}", headers=headers
        )
        assert detail.status_code == 200
        assert "confusion_matrix" in detail.json()["figures"]

    async def test_list_experiments(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, dataset_id = await _prepare(client, unique_email)
        await client.post(
            f"{PROJECTS}/{project_id}/experiments",
            headers=headers,
            json={
                "name": "E1",
                "dataset_id": dataset_id,
                "task_type": "classification",
                "target_column": "target",
                "algorithms": ["decision_tree"],
                "cv_folds": 2,
            },
        )
        listing = await client.get(f"{PROJECTS}/{project_id}/experiments", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["meta"]["total"] == 1


class TestExperimentValidation:
    async def test_unknown_algorithm_rejected(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, dataset_id = await _prepare(client, unique_email)
        resp = await client.post(
            f"{PROJECTS}/{project_id}/experiments",
            headers=headers,
            json={
                "name": "Bad",
                "dataset_id": dataset_id,
                "task_type": "classification",
                "target_column": "target",
                "algorithms": ["nonexistent_algo"],
            },
        )
        assert resp.status_code == 422

    async def test_missing_target_rejected(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, dataset_id = await _prepare(client, unique_email)
        resp = await client.post(
            f"{PROJECTS}/{project_id}/experiments",
            headers=headers,
            json={
                "name": "No target",
                "dataset_id": dataset_id,
                "task_type": "classification",
            },
        )
        assert resp.status_code == 422

    async def test_clustering_not_supported(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, dataset_id = await _prepare(client, unique_email)
        resp = await client.post(
            f"{PROJECTS}/{project_id}/experiments",
            headers=headers,
            json={
                "name": "Cluster",
                "dataset_id": dataset_id,
                "task_type": "clustering",
            },
        )
        assert resp.status_code == 422
