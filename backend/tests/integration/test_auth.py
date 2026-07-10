"""Integration tests for the authentication endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

API = "/api/v1/auth"


async def _register(client: AsyncClient, email: str, password: str = "Passw0rd!") -> dict:
    resp = await client.post(
        f"{API}/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    return resp


class TestRegistration:
    async def test_register_returns_user_and_tokens(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        resp = await _register(client, unique_email)
        assert resp.status_code == 201
        body = resp.json()
        assert body["user"]["email"] == unique_email
        assert body["tokens"]["access_token"]
        assert body["tokens"]["token_type"] == "bearer"
        # Default role assigned.
        assert any(r["name"] == "viewer" for r in body["user"]["roles"])

    async def test_duplicate_email_conflicts(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        await _register(client, unique_email)
        resp = await _register(client, unique_email)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "conflict"

    async def test_weak_password_is_rejected(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        resp = await client.post(
            f"{API}/register",
            json={"email": unique_email, "password": "onlyletters"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        await _register(client, unique_email, "Passw0rd!")
        resp = await client.post(
            f"{API}/login", json={"email": unique_email, "password": "Passw0rd!"}
        )
        assert resp.status_code == 200
        assert resp.json()["access_token"]

    async def test_login_wrong_password(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        await _register(client, unique_email, "Passw0rd!")
        resp = await client.post(
            f"{API}/login", json={"email": unique_email, "password": "nope"}
        )
        assert resp.status_code == 401

    async def test_login_unknown_user(self, client: AsyncClient, seeded: None) -> None:
        resp = await client.post(
            f"{API}/login", json={"email": "ghost@example.com", "password": "whatever1!"}
        )
        assert resp.status_code == 401


class TestMeAndAuthGuard:
    async def test_me_requires_authentication(self, client: AsyncClient) -> None:
        resp = await client.get(f"{API}/me")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "not_authenticated"

    async def test_me_returns_profile(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        tokens = (await _register(client, unique_email)).json()["tokens"]
        resp = await client.get(
            f"{API}/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == unique_email

    async def test_invalid_token_rejected(self, client: AsyncClient) -> None:
        resp = await client.get(
            f"{API}/me", headers={"Authorization": "Bearer not.a.jwt"}
        )
        assert resp.status_code == 401


class TestRefreshRotation:
    async def test_refresh_issues_new_pair(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        tokens = (await _register(client, unique_email)).json()["tokens"]
        resp = await client.post(
            f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert resp.status_code == 200
        assert resp.json()["refresh_token"] != tokens["refresh_token"]

    async def test_rotated_token_cannot_be_reused(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        tokens = (await _register(client, unique_email)).json()["tokens"]
        old_refresh = tokens["refresh_token"]
        first = await client.post(f"{API}/refresh", json={"refresh_token": old_refresh})
        assert first.status_code == 200
        # Reusing the now-rotated token must fail.
        replay = await client.post(f"{API}/refresh", json={"refresh_token": old_refresh})
        assert replay.status_code == 401
        assert replay.json()["error"]["code"] == "refresh_invalid"

    async def test_logout_revokes_refresh_token(
        self, client: AsyncClient, seeded: None, unique_email: str
    ) -> None:
        tokens = (await _register(client, unique_email)).json()["tokens"]
        logout = await client.post(
            f"{API}/logout", json={"refresh_token": tokens["refresh_token"]}
        )
        assert logout.status_code == 204
        resp = await client.post(
            f"{API}/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert resp.status_code == 401


class TestSuperuser:
    async def test_superuser_can_log_in(
        self, client: AsyncClient, superuser: dict[str, str]
    ) -> None:
        resp = await client.post(f"{API}/login", json=superuser)
        assert resp.status_code == 200
        access = resp.json()["access_token"]
        me = await client.get(
            f"{API}/me", headers={"Authorization": f"Bearer {access}"}
        )
        assert me.json()["is_superuser"] is True
        assert any(r["name"] == "admin" for r in me.json()["roles"])
