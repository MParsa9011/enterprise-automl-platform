"""Integration tests for the dataset management endpoints."""

from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

AUTH = "/api/v1/auth"
PROJECTS = "/api/v1/projects"


def _csv_bytes(rows: int = 6) -> bytes:
    """Build a small deterministic CSV payload for uploads."""
    lines = ["age,income,gender,churned"]
    data = [
        (25, 50000, "M", 0),
        (32, 64000, "F", 1),
        (47, 120000, "F", 0),
        (38, 80000, "M", 0),
        (51, 95000, "F", 1),
        (29, 70000, "M", 0),
    ]
    for i in range(rows):
        age, income, gender, churned = data[i % len(data)]
        lines.append(f"{age},{income},{gender},{churned}")
    return ("\n".join(lines) + "\n").encode()


async def _setup_project(client: AsyncClient, email: str) -> tuple[dict[str, str], str]:
    """Register a user and create a project; return (headers, project_id)."""
    reg = await client.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Passw0rd!", "full_name": "DS"},
    )
    headers = {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}
    proj = await client.post(PROJECTS, json={"name": "ML Project"}, headers=headers)
    return headers, proj.json()["id"]


async def _upload(
    client: AsyncClient, headers: dict[str, str], project_id: str, name: str = "Customers"
):
    return await client.post(
        f"{PROJECTS}/{project_id}/datasets",
        headers=headers,
        data={"name": name, "description": "customer table"},
        files={"file": ("customers.csv", io.BytesIO(_csv_bytes()), "text/csv")},
    )


class TestDatasetUpload:
    async def test_upload_creates_dataset_with_profile(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id = await _setup_project(client, unique_email)
        resp = await _upload(client, headers, project_id)
        assert resp.status_code == 201
        body = resp.json()
        assert body["slug"] == "customers"
        assert body["latest_version"] == 1
        assert len(body["versions"]) == 1
        version = body["versions"][0]
        assert version["n_rows"] == 6
        assert version["n_columns"] == 4

    async def test_version_statistics_are_computed(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id = await _setup_project(client, unique_email)
        dataset_id = (await _upload(client, headers, project_id)).json()["id"]
        resp = await client.get(f"/api/v1/datasets/{dataset_id}/versions/1", headers=headers)
        assert resp.status_code == 200
        stats = resp.json()["statistics"]
        assert stats["overview"]["n_rows"] == 6
        assert "age" in stats["numeric"]
        assert "gender" in stats["categorical"]
        assert "correlations" in stats

    async def test_malformed_file_is_rejected(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id = await _setup_project(client, unique_email)
        resp = await client.post(
            f"{PROJECTS}/{project_id}/datasets",
            headers=headers,
            data={"name": "Bad"},
            files={"file": ("bad.xyz", io.BytesIO(b"not a table"), "text/plain")},
        )
        assert resp.status_code == 422


class TestDatasetVersioning:
    async def test_add_version_increments(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id = await _setup_project(client, unique_email)
        dataset_id = (await _upload(client, headers, project_id)).json()["id"]
        resp = await client.post(
            f"/api/v1/datasets/{dataset_id}/versions",
            headers=headers,
            files={"file": ("v2.csv", io.BytesIO(_csv_bytes()), "text/csv")},
        )
        assert resp.status_code == 201
        assert resp.json()["version"] == 2
        detail = await client.get(f"/api/v1/datasets/{dataset_id}", headers=headers)
        assert detail.json()["latest_version"] == 2

    async def test_download_returns_original_bytes(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers, project_id = await _setup_project(client, unique_email)
        dataset_id = (await _upload(client, headers, project_id)).json()["id"]
        resp = await client.get(
            f"/api/v1/datasets/{dataset_id}/versions/1/download", headers=headers
        )
        assert resp.status_code == 200
        assert resp.content == _csv_bytes()


class TestDatasetAuthorization:
    async def test_upload_requires_permission(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/projects/" + "0" * 8 + "/datasets")
        assert resp.status_code in (401, 422)

    async def test_cannot_read_other_projects_dataset(
        self, client: AsyncClient, seeded: None
    ) -> None:
        owner_headers, project_id = await _setup_project(client, "owner@example.com")
        dataset_id = (await _upload(client, owner_headers, project_id)).json()["id"]
        intruder_headers, _ = await _setup_project(client, "intruder@example.com")
        resp = await client.get(f"/api/v1/datasets/{dataset_id}", headers=intruder_headers)
        assert resp.status_code == 404
