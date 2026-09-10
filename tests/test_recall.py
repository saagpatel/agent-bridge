from __future__ import annotations

import aiosqlite
import pytest

from agent_bridge.tools.activity import log_activity
from agent_bridge.tools.context import update_section
from agent_bridge.tools.handoffs import create_handoff
from agent_bridge.tools.recall import recall


async def test_recall_finds_section(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="roadmap", content="ship the kraken")
    hits = await recall(db, query="kraken")
    assert any(h["source_type"] == "section" for h in hits)


async def test_recall_across_types(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="s", content="orbital mechanics")
    await log_activity(db, caller="codex", project="orbital", summary="built orbital sim")
    await create_handoff(db, caller="claude-ai", project="orbital-followup")
    hits = await recall(db, query="orbital", limit=50)
    types = {h["source_type"] for h in hits}
    assert {"section", "activity", "handoff"} <= types


async def test_scope_filter(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="s", content="widget")
    await log_activity(db, caller="codex", project="widget", summary="widget work")
    hits = await recall(db, query="widget", scope="activity")
    assert all(h["source_type"] == "activity" for h in hits)


async def test_or_semantics(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="alpha only")
    await log_activity(db, caller="codex", project="p", summary="beta only")
    # Multi-token query matches rows containing ANY token.
    hits = await recall(db, query="alpha beta", limit=50)
    assert len(hits) == 2


async def test_operators_sanitized(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="quoted text here")
    # A raw query full of FTS operators must not raise; it's treated as terms.
    hits = await recall(db, query='"text" AND (quoted OR *)', limit=50)
    assert any(
        "text" in (h["snippet"] or "").lower() or h["source_type"] == "activity" for h in hits
    )


async def test_empty_query_returns_empty(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="something")
    assert await recall(db, query="   !!!   ") == []


async def test_invalid_scope_rejected(db: aiosqlite.Connection):
    with pytest.raises(ValueError, match="Invalid scope"):
        await recall(db, query="x", scope="bogus")
