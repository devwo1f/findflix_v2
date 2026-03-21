import pytest
from httpx import AsyncClient

from app.db.models import User


pytestmark = pytest.mark.asyncio


class TestSignup:
    async def test_signup_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "strongpassword123",
                "display_name": "New User",
                "region": "US",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_signup_duplicate_email(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": test_user.email,
                "password": "anotherpassword123",
            },
        )
        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    async def test_signup_invalid_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "not-an-email",
                "password": "password123",
            },
        )
        assert response.status_code == 422

    async def test_signup_short_password(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/signup",
            json={
                "email": "short@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nobody@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401


class TestTokenRefresh:
    async def test_refresh_token(self, client: AsyncClient, test_user: User):
        # First login to get tokens
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email, "password": "testpassword123"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_invalid_token(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )
        assert response.status_code == 401


class TestProtectedRoutes:
    async def test_get_me_authenticated(self, client: AsyncClient, auth_headers: dict, test_user: User):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["display_name"] == test_user.display_name

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401

    async def test_password_reset(self, client: AsyncClient, test_user: User):
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": test_user.email},
        )
        assert response.status_code == 202

    async def test_password_reset_unknown_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/password-reset",
            json={"email": "unknown@example.com"},
        )
        # Should still return 202 to prevent email enumeration
        assert response.status_code == 202
