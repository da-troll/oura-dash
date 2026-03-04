"""Unit tests for long-term memory helpers."""

from app.chat import (
    _build_memory_prompt_block,
    _cosine_similarity,
    _normalize_memory_content,
)


def test_normalize_memory_content_collapses_whitespace():
    value = _normalize_memory_content("  Likes  low-noise   notifications  ")
    assert value == "likes low-noise notifications"


def test_cosine_similarity_identical_vectors():
    assert _cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_build_memory_prompt_block_respects_token_budget():
    memories = [
        {"memory_type": "preference", "content": "Prefers concise answers", "confidence": 0.9},
        {"memory_type": "goal", "content": "Wants weekly sleep trend review", "confidence": 0.8},
        {"memory_type": "episodic", "content": "Had a stressful work week in January", "confidence": 0.7},
    ]
    block, tokens = _build_memory_prompt_block(memories, max_tokens=30)
    assert block.startswith("Relevant long-term memory")
    assert tokens <= 30
