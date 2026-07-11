"""Integration tests for the model registry, prediction and notifications."""

from __future__ import annotations

import io
import random

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio, pytest.mark.ml]

AUTH = "/api/v1/auth"
PROJECTS = "/api/v1/projects"


def _csv(n: int = 60) -> bytes:
    rng = random.Random(7)
    rows = ["x1,x2,x3,target"]
    for _ in range(n):
        label = rng.randint(0, 1)
        rows.append(
            f"{rng.gauss(2 if label else -2,1):.3f},"
            f"{rng.gauss(1 if label else -1,1):.3f},"
            f"{rng.gauss(0,1):.3f},{label}"
        )
    return ("\n".join(rows) + "\n").encode()


async def _train(client: AsyncClient, email: str) -> tuple[dict[str, str], str, str]:
    """Register a user and run an experiment; return (headers, project_id, run_id)."""
    reg = await client.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Passw0rd!", "full_name": "DS"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
    project_id = (await client.post(PROJECTS, json={"name": "P"}, headers=headers)).json()["id"]
    dataset_id = (
        await client.post(
            f"{PROJECTS}/{project_id}/datasets",
            headers=headers,
            data={"name": "Blobs"},
            files={"file": ("b.csv", io.BytesIO(_csv()), "text/csv")},
        )
    ).json()["id"]
    exp = await client.post(
        f"{PROJECTS}/{project_id}/experiments",
        headers=headers,
        json={
            "name": "E",
            "dataset_id": dataset_id,
            "task_type": "classification",
            "target_column": "target",
            "algorithms": ["logistic_regression"],
            "cv_folds": 2,
        },
    )
    run_id = exp.json()["best_run_id"]
    return headers, project_id, run_id


class TestModelRegistry:
    async def test_register_and_deploy(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, run_id = await _train(client, unique_email)
        resp = await client.post(
            "/api/v1/models",
            headers=headers,
            json={"run_id": run_id, "name": "Churn Model", "deploy": True},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["version"] == 1
        assert body["stage"] == "production"
        assert body["feature_schema"]

    async def test_second_version_and_deploy_archives_previous(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, run_id = await _train(client, unique_email)
        first = await client.post(
            "/api/v1/models",
            headers=headers,
            json={"run_id": run_id, "name": "Churn Model", "deploy": True},
        )
        second = await client.post(
            "/api/v1/models",
            headers=headers,
            json={"run_id": run_id, "name": "Churn Model", "deploy": True},
        )
        assert second.json()["version"] == 2
        # The first version is archived after the second is deployed.
        reread = await client.get(f"/api/v1/models/{first.json()['id']}", headers=headers)
        assert reread.json()["stage"] == "archived"

    async def test_compare_models(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, run_id = await _train(client, unique_email)
        a = await client.post(
            "/api/v1/models", headers=headers, json={"run_id": run_id, "name": "A"}
        )
        b = await client.post(
            "/api/v1/models", headers=headers, json={"run_id": run_id, "name": "B"}
        )
        resp = await client.get(
            "/api/v1/models/compare",
            headers=headers,
            params={"model_ids": [a.json()["id"], b.json()["id"]]},
        )
        assert resp.status_code == 200
        assert len(resp.json()["models"]) == 2


class TestPrediction:
    async def test_predict_returns_labels_and_probabilities(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, run_id = await _train(client, unique_email)
        model_id = (
            await client.post(
                "/api/v1/models",
                headers=headers,
                json={"run_id": run_id, "name": "M", "deploy": True},
            )
        ).json()["id"]

        resp = await client.post(
            f"/api/v1/models/{model_id}/predict",
            headers=headers,
            json={
                "records": [{"x1": 2.0, "x2": 1.0, "x3": 0.0}, {"x1": -2.0, "x2": -1.0, "x3": 0.0}]
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["predictions"]) == 2
        assert body["predictions"][0]["probabilities"] is not None

    async def test_predict_rejects_missing_features(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, run_id = await _train(client, unique_email)
        model_id = (
            await client.post(
                "/api/v1/models", headers=headers, json={"run_id": run_id, "name": "M"}
            )
        ).json()["id"]
        resp = await client.post(
            f"/api/v1/models/{model_id}/predict",
            headers=headers,
            json={"records": [{"x1": 1.0}]},
        )
        assert resp.status_code == 422


class TestNotifications:
    async def test_deploy_emits_notification(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id, run_id = await _train(client, unique_email)
        await client.post(
            "/api/v1/models",
            headers=headers,
            json={"run_id": run_id, "name": "M", "deploy": True},
        )
        listing = await client.get("/api/v1/notifications", headers=headers)
        assert listing.status_code == 200
        assert listing.json()["meta"]["total"] >= 1

        count = await client.get("/api/v1/notifications/unread-count", headers=headers)
        assert count.json()["unread"] >= 1

        notif_id = listing.json()["items"][0]["id"]
        read = await client.post(f"/api/v1/notifications/{notif_id}/read", headers=headers)
        assert read.json()["read_at"] is not None
