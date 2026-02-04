"""Oura OAuth token management."""

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import psycopg

from app.db import get_db
from app.settings import settings


class OAuthError(Exception):
    """OAuth-related error."""

    pass


class TokenExpiredError(OAuthError):
    """Token has expired and refresh failed."""

    pass


async def get_auth_url() -> tuple[str, str]:
    """Generate Oura OAuth authorization URL.

    Returns:
        Tuple of (authorization_url, state)
    """
    state = secrets.token_urlsafe(32)

    params = {
        "response_type": "code",
        "client_id": settings.oura_client_id,
        "redirect_uri": settings.oura_redirect_uri,
        "scope": settings.oura_scopes,
        "state": state,
    }

    url = f"{settings.oura_auth_url}?{urlencode(params)}"
    return url, state


async def exchange_code(code: str) -> dict:
    """Exchange authorization code for tokens.

    Args:
        code: Authorization code from OAuth callback

    Returns:
        Token response dict with access_token, refresh_token, expires_in, etc.

    Raises:
        OAuthError: If token exchange fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.oura_token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.oura_redirect_uri,
                "client_id": settings.oura_client_id,
                "client_secret": settings.oura_client_secret,
            },
        )

        if response.status_code != 200:
            error_detail = response.text
            raise OAuthError(f"Token exchange failed: {error_detail}")

        return response.json()


async def refresh_access_token(refresh_token: str) -> dict:
    """Refresh the access token using a refresh token.

    Args:
        refresh_token: The refresh token

    Returns:
        New token response dict

    Raises:
        OAuthError: If refresh fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.oura_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": settings.oura_client_id,
                "client_secret": settings.oura_client_secret,
            },
        )

        if response.status_code != 200:
            error_detail = response.text
            raise OAuthError(f"Token refresh failed: {error_detail}")

        return response.json()


async def store_tokens(tokens: dict) -> None:
    """Store OAuth tokens in the database.

    Args:
        tokens: Token response dict from Oura
    """
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=tokens["expires_in"])

    async with get_db() as conn:
        await conn.execute(
            """
            INSERT INTO oura_auth (id, access_token, refresh_token, expires_at, token_type, scope)
            VALUES (1, %(access_token)s, %(refresh_token)s, %(expires_at)s, %(token_type)s, %(scope)s)
            ON CONFLICT (id) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                expires_at = EXCLUDED.expires_at,
                token_type = EXCLUDED.token_type,
                scope = EXCLUDED.scope,
                updated_at = NOW()
            """,
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": expires_at,
                "token_type": tokens.get("token_type", "Bearer"),
                "scope": tokens.get("scope"),
            },
        )
        await conn.commit()


async def get_auth_record() -> dict | None:
    """Get the current auth record from database.

    Returns:
        Auth record dict or None if not connected
    """
    async with get_db() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT * FROM oura_auth WHERE id = 1")
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_valid_access_token() -> str:
    """Get a valid access token, refreshing if necessary.

    Returns:
        Valid access token

    Raises:
        OAuthError: If not connected to Oura
        TokenExpiredError: If refresh fails
    """
    auth = await get_auth_record()

    if not auth:
        raise OAuthError("Not connected to Oura. Please authorize first.")

    # Check if token expires within 2 minutes
    expires_at = auth["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    buffer_time = datetime.now(timezone.utc) + timedelta(minutes=2)

    if expires_at <= buffer_time:
        # Token is expired or about to expire, refresh it
        try:
            new_tokens = await refresh_access_token(auth["refresh_token"])
            await store_tokens(new_tokens)
            return new_tokens["access_token"]
        except OAuthError as e:
            # Refresh failed, clear auth and raise
            await clear_auth()
            raise TokenExpiredError(
                "Oura connection expired. Please reconnect."
            ) from e

    return auth["access_token"]


async def get_auth_status() -> dict:
    """Get current authentication status.

    Returns:
        Dict with connected status and expiration info
    """
    auth = await get_auth_record()

    if not auth:
        return {"connected": False}

    expires_at = auth["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    scopes = auth.get("scope", "").split() if auth.get("scope") else []

    return {
        "connected": True,
        "expires_at": expires_at.isoformat(),
        "scopes": scopes,
    }


async def clear_auth() -> None:
    """Clear the stored authentication."""
    async with get_db() as conn:
        await conn.execute("DELETE FROM oura_auth WHERE id = 1")
        await conn.commit()
