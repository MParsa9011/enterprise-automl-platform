"""Integration tests for the project (workspace) endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

AUTH = "/api/v1/auth"
PROJECTS = "/api/v1/projects"


async def _auth_headers(client: AsyncClient, email: str) -> dict[str, str]:
    """Register a user and return an Authorization header for them."""
    resp = await client.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Passw0rd!", "full_name": "PM"},
    )
    token = resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestProjectCrud:
    async def test_create_and_get(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers = await _auth_headers(client, unique_email)
        created = await client.post(
            PROJECTS, json={"name": "Churn Model", "description": "Q3"}, headers=headers
        )
        assert created.status_code == 201
        body = created.json()
        assert body["slug"] == "churn-model"
        assert body["owner"]["email"] == unique_email

        fetched = await client.get(f"{PROJECTS}/{body['id']}", headers=headers)
        assert fetched.status_code == 200
        assert fetched.json()["name"] == "Churn Model"

    async def test_duplicate_name_gets_unique_slug(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers = await _auth_headers(client, unique_email)
        first = await client.post(PROJECTS, json={"name": "Report"}, headers=headers)
        second = await client.post(PROJECTS, json={"name": "Report"}, headers=headers)
        assert first.json()["slug"] == "report"
        assert second.json()["slug"] == "report-2"

    async def test_list_is_paginated_and_scoped(
        self, client: AsyncClient, seeded: None
    ) -> None:
        headers = await _auth_headers(client, "owner-a@example.com")
        other = await _auth_headers(client, "owner-b@example.com")
        for i in range(3):
            await client.post(PROJECTS, json={"name": f"P{i}"}, headers=headers)
        await client.post(PROJECTS, json={"name": "Other"}, headers=other)

        listing = await client.get(f"{PROJECTS}?page=1&size=2", headers=headers)
        body = listing.json()
        assert body["meta"]["total"] == 3
        assert body["meta"]["pages"] == 2
        assert len(body["items"]) == 2

    async def test_update_changes_slug(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers = await _auth_headers(client, unique_email)
        created = await client.post(PROJECTS, json={"name": "Old"}, headers=headers)
        pid = created.json()["id"]
        updated = await client.patch(
            f"{PROJECTS}/{pid}", json={"name": "New Name"}, headers=headers
        )
        assert updated.status_code == 200
        assert updated.json()["slug"] == "new-name"

    async def test_delete_then_get_returns_404(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        headers = await _auth_headers(client, unique_email)
        created = await client.post(PROJECTS, json={"name": "Temp"}, headers=headers)
        pid = created.json()["id"]
        deleted = await client.delete(f"{PROJECTS}/{pid}", headers=headers)
        assert deleted.status_code == 204
        assert (await client.get(f"{PROJECTS}/{pid}", headers=headers)).status_code == 404


class TestProjectAuthorization:
    async def test_requires_authentication(self, client: AsyncClient) -> None:
        assert (await client.get(PROJECTS)).status_code == 401

    async def test_cannot_access_other_users_project(
        self, client: AsyncClient, seeded: None
    ) -> None:
        owner = await _auth_headers(client, "owner@example.com")
        intruder = await _auth_headers(client, "intruder@example.com")
        created = await client.post(PROJECTS, json={"name": "Secret"}, headers=owner)
        pid = created.json()["id"]
        # Cross-owner access is indistinguishable from "not found".
        assert (await client.get(f"{PROJECTS}/{pid}", headers=intruder)).status_code == 404
