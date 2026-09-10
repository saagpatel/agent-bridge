from __future__ import annotations

import aiosqlite
import pytest

from agent_bridge import config
from agent_bridge.tools.activity import get_recent_activity, log_activity


async def test_log_and_read_back(db: aiosqlite.Connection):
    result = await log_activity(db, caller="codex", project="proj", summary="built thing")
    assert result["ok"] is True
    recent = await get_recent_activity(db, limit=10)
    assert len(recent) == 1
    assert recent[0]["summary"] == "built thing"
    assert recent[0]["tags"] == []


async def test_tags_round_trip(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="s", tags=["SHIPPED", "v1"])
    recent = await get_recent_activity(db, limit=1)
    assert recent[0]["tags"] == ["SHIPPED", "v1"]


async def test_unknown_agent_rejected(db: aiosqlite.Connection):
    with pytest.raises(ValueError, match="Unknown agent"):
        await log_activity(db, caller="nope", project="p", summary="s")


async def test_filter_by_source(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="from codex")
    await log_activity(db, caller="claude-code", project="p", summary="from cc")
    only_codex = await get_recent_activity(db, source="codex")
    assert len(only_codex) == 1
    assert only_codex[0]["source"] == "codex"


async def test_filter_since(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="old", timestamp="2026-01-01")
    await log_activity(db, caller="codex", project="p", summary="new", timestamp="2026-06-01")
    recent = await get_recent_activity(db, since="2026-03-01")
    assert [r["summary"] for r in recent] == ["new"]


async def test_retention_enforced(db: aiosqlite.Connection, monkeypatch):
    monkeypatch.setattr(config, "ACTIVITY_RETENTION_PER_SOURCE", 3)
    for i in range(6):
        await log_activity(db, caller="codex", project="p", summary=f"e{i}")
    recent = await get_recent_activity(db, limit=100, source="codex")
    assert len(recent) == 3
