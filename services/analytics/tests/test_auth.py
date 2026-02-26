"""Tests for user authentication: register, login, session management."""

import pytest


async def test_register_success(client):
    """Register a new user and get session token."""
    res = await client.post("/auth/register", json={"email": "new@example.com", "password": "securepass123"})
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "new@example.com"
    assert "user_id" in data
    assert "session_token" in data
    assert "expires_at" in data


async def test_register_short_password(client):
    """Password < 8 chars should be rejected."""
    res = await client.post("/auth/register", json={"email": "short@example.com", "password": "abc"})
    assert res.status_code in (400, 422)  # 422 from Pydantic min_length, 400 from manual check


async def test_register_duplicate_email(client):
    """Duplicate email (exact match) should return 409."""
    await client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
    res = await client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert res.status_code == 409


async def test_register_case_insensitive_email(client):
    """Emails should be case-insensitive for uniqueness."""
    await client.post("/auth/register", json={"email": "Case@Example.com", "password": "password123"})
    res = await client.post("/auth/register", json={"email": "case@example.com", "password": "password123"})
    assert res.status_code == 409


async def test_login_success(client):
    """Login with valid credentials."""
    await client.post("/auth/register", json={"email": "login@example.com", "password": "password123"})
    res = await client.post("/auth/login", json={"email": "login@example.com", "password": "password123"})
    assert res.status_code == 200
    data = res.json()
    assert "session_token" in data
    assert data["email"] == "login@example.com"


async def test_login_case_insensitive(client):
    """Login should work with different email casing."""
    await client.post("/auth/register", json={"email": "CaseLogin@Example.com", "password": "password123"})
    res = await client.post("/auth/login", json={"email": "caselogin@example.com", "password": "password123"})
    assert res.status_code == 200


async def test_login_wrong_password(client):
    """Wrong password should return 401."""
    await client.post("/auth/register", json={"email": "wrong@example.com", "password": "password123"})
    res = await client.post("/auth/login", json={"email": "wrong@example.com", "password": "wrongpass"})
    assert res.status_code == 401


async def test_login_nonexistent_user(client):
    """Nonexistent email should return 401."""
    res = await client.post("/auth/login", json={"email": "noone@example.com", "password": "password123"})
    assert res.status_code == 401


async def test_me_with_valid_token(client):
    """GET /auth/me with valid token should return user info."""
    from tests.conftest import register_and_login, auth_headers

    user = await register_and_login(client, "me@example.com", "password123")
    res = await client.get("/auth/me", headers=auth_headers(user["token"]))
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me@example.com"
    assert data["user_id"] == user["user_id"]


async def test_me_without_token(client):
    """GET /auth/me without token should return 401."""
    res = await client.get("/auth/me")
    assert res.status_code == 401


async def test_me_with_invalid_token(client):
    """GET /auth/me with garbage token should return 401."""
    res = await client.get("/auth/me", headers={"Authorization": "Bearer invalid_token"})
    assert res.status_code == 401


async def test_logout(client):
    """Logout should invalidate the session token."""
    from tests.conftest import register_and_login, auth_headers

    user = await register_and_login(client, "logout@example.com", "password123")
    headers = auth_headers(user["token"])

    # Logout
    res = await client.post("/auth/logout", headers=headers)
    assert res.status_code == 200

    # Token should no longer work
    res = await client.get("/auth/me", headers=headers)
    assert res.status_code == 401


async def test_logout_requires_auth(client):
    """POST /auth/logout without token should return 401."""
    res = await client.post("/auth/logout")
    assert res.status_code == 401


async def test_login_rate_limit(client):
    """Rapid login attempts should eventually return 429."""
    # Register a user first
    await client.post(
        "/auth/register",
        json={"email": "ratelimit@example.com", "password": "password123"},
    )

    # Reset the rate limiter state for a clean test
    from app.main import login_rate_limiter
    login_rate_limiter._attempts.clear()

    # Fire off max_attempts + 1 login requests with wrong password
    for i in range(login_rate_limiter.max_attempts):
        res = await client.post(
            "/auth/login",
            json={"email": "ratelimit@example.com", "password": "wrongpass"},
        )
        assert res.status_code == 401, f"Attempt {i+1} should return 401"

    # The next request should be rate limited
    res = await client.post(
        "/auth/login",
        json={"email": "ratelimit@example.com", "password": "wrongpass"},
    )
    assert res.status_code == 429


async def test_register_invalid_email(client):
    """Register with invalid email should return 422."""
    res = await client.post(
        "/auth/register",
        json={"email": "notanemail", "password": "password123"},
    )
    assert res.status_code == 422


async def test_health_check(client):
    """Health check should not require auth."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["ok"] is True
