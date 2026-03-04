"""Tests for chat agent endpoints."""

import uuid

import pytest

from app.settings import settings
from tests.conftest import auth_headers, register_and_login


async def test_chat_endpoints_require_auth(client):
    """Chat endpoints should require authentication."""
    res = await client.post("/chat", json={"message": "hello"})
    assert res.status_code == 401

    res = await client.get("/chat/conversations")
    assert res.status_code == 401

    res = await client.get("/chat/conversations/some-id")
    assert res.status_code == 401

    res = await client.delete("/chat/conversations/some-id")
    assert res.status_code == 401


async def test_chat_status_no_auth_required(client):
    """Chat status endpoint should work without auth."""
    res = await client.get("/chat/status")
    assert res.status_code == 200
    data = res.json()
    assert "enabled" in data


async def test_chat_feature_flag_disabled(client):
    """When chat_enabled is False, chat endpoints should return 403."""
    user = await register_and_login(client, "chat@example.com", "password123")
    headers = auth_headers(user["token"])

    # By default chat_enabled=False
    res = await client.post("/chat", json={"message": "test"}, headers=headers)
    assert res.status_code == 403

    res = await client.get("/chat/conversations", headers=headers)
    assert res.status_code == 403

    res = await client.delete("/chat/conversations/fake-id", headers=headers)
    assert res.status_code == 403


async def test_chat_status_returns_disabled(client):
    """Chat status should report disabled by default."""
    res = await client.get("/chat/status")
    assert res.status_code == 200
    assert res.json()["enabled"] is False


async def test_get_conversation_supports_pagination(client, db_conn, monkeypatch):
    """Conversation endpoint should support paginated fetches for long threads."""
    monkeypatch.setattr(settings, "chat_enabled", True)

    user = await register_and_login(client, "chat-pagination@example.com", "password123")
    headers = auth_headers(user["token"])
    conversation_id = str(uuid.uuid4())

    await db_conn.execute(
        "INSERT INTO chat_conversations (id, user_id, title) VALUES (%s, %s, %s)",
        (conversation_id, user["user_id"], "Long conversation"),
    )

    for idx in range(1, 6):
        await db_conn.execute(
            """
            INSERT INTO chat_messages (user_id, conversation_id, role, content, created_at)
            VALUES (%s, %s, 'assistant', %s, NOW() - (%s * INTERVAL '1 minute'))
            """,
            (user["user_id"], conversation_id, f"msg-{idx}", 6 - idx),
        )
    await db_conn.commit()

    newest_page = await client.get(
        f"/chat/conversations/{conversation_id}?limit=2",
        headers=headers,
    )
    assert newest_page.status_code == 200
    newest = newest_page.json()
    assert [m["content"] for m in newest] == ["msg-4", "msg-5"]

    older_page = await client.get(
        f"/chat/conversations/{conversation_id}?limit=2&before={newest[0]['created_at']}",
        headers=headers,
    )
    assert older_page.status_code == 200
    older = older_page.json()
    assert [m["content"] for m in older] == ["msg-2", "msg-3"]
