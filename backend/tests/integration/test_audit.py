"""Integration tests for audit logging and its access control."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

AUTH = "/api/v1/auth"


async def _headers(client: AsyncClient, email: str) -> dict[str, str]:
    reg = await client.post(
        f"{AUTH}/register",
        json={"email": email, "password": "Passw0rd!", "full_name": "U"},
    )
    return {"Authorization": f"Bearer {reg.json()['tokens']['access_token']}"}


class TestAuditLogging:
    async def test_mutating_requests_are_recorded(
        self, client: AsyncClient, seeded: None, superuser: dict[str, str], unique_email: str
    ) -> None:
        # A mutating request (registration) should be audited by the middleware.
        headers = await _headers(client, unique_email)
        await client.post("/api/v1/projects", json={"name": "Audited"}, headers=headers)

        login = await client.post(f"{AUTH}/login", json=superuser)
        admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = await client.get("/api/v1/audit-logs", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["total"] >= 1
        actions = {entry["action"] for entry in body["items"]}
        assert any("/api/v1/projects" in action for action in actions)

    async def test_audit_requires_permission(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        # A default data-scientist user lacks the audit:read permission.
        headers = await _headers(client, unique_email)
        resp = await client.get("/api/v1/audit-logs", headers=headers)
        assert resp.status_code == 403
