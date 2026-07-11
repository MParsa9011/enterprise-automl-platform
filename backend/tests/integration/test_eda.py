"""Integration tests for the EDA and feature-preview endpoints."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

AUTH = "/api/v1/auth"
PROJECTS = "/api/v1/projects"


def _csv_bytes() -> bytes:
    rows = [
        "age,income,gender,churned",
        "25,50000,M,0",
        "32,64000,F,1",
        "47,120000,F,0",
        "38,80000,M,0",
        "51,95000,F,1",
        "29,70000,M,0",
        "44,88000,F,1",
        "36,61000,M,0",
    ]
    return ("\n".join(rows) + "\n").encode()


async def _upload_dataset(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    reg = await client.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Passw0rd!", "full_name": "DS"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
    project_id = (await client.post(PROJECTS, json={"name": "P"}, headers=headers)).json()["id"]
    dataset = await client.post(
        f"{PROJECTS}/{project_id}/datasets",
        headers=headers,
        data={"name": "Customers"},
        files={"file": ("customers.csv", io.BytesIO(_csv_bytes()), "text/csv")},
    )
    return headers, dataset.json()["id"]


class TestEda:
    async def test_eda_returns_figures(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, dataset_id = await _upload_dataset(client, unique_email)
        resp = await client.get(
            f"/api/v1/datasets/{dataset_id}/versions/1/eda", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["correlation_heatmap"] is not None
        assert "age" in body["histograms"]
        assert "gender" in body["categorical"]
        # Plotly figure specs carry data + layout.
        assert "data" in body["missing_values"]


class TestFeaturePreview:
    async def test_preview_onehot(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, dataset_id = await _upload_dataset(client, unique_email)
        resp = await client.post(
            f"/api/v1/datasets/{dataset_id}/versions/1/feature-preview",
            headers=headers,
            json={"target": "churned", "encoding": "onehot", "scaling": "standard"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["n_features_out"] == 4
        assert set(body["numeric_columns"]) == {"age", "income"}

    async def test_preview_rejects_unknown_target(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, dataset_id = await _upload_dataset(client, unique_email)
        resp = await client.post(
            f"/api/v1/datasets/{dataset_id}/versions/1/feature-preview",
            headers=headers,
            json={"target": "does_not_exist"},
        )
        assert resp.status_code == 422

    async def test_preview_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/datasets/" + "0" * 8 + "/versions/1/feature-preview", json={}
        )
        assert resp.status_code in (401, 422)
