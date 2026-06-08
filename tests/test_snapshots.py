from __future__ import annotations

import aiosqlite
import pytest

from agent_bridge import config
from agent_bridge.db import collect_fts_metrics
from agent_bridge.tools.snapshots import get_latest_snapshot, save_snapshot


async def test_save_and_get_latest(db: aiosqlite.Connection):
    await save_snapshot(db, caller="codex", data={"active": ["recall"]})
    snap = await get_latest_snapshot(db, system="codex")
    assert snap is not None
    assert snap["data"] == {"active": ["recall"]}


async def test_latest_returns_most_recent(db: aiosqlite.Connection):
    await save_snapshot(db, caller="codex", data={"v": 1}, snapshot_date="2026-01-01")
    await save_snapshot(db, caller="codex", data={"v": 2}, snapshot_date="2026-02-01")
    snap = await get_latest_snapshot(db, system="codex")
    assert snap["data"]["v"] == 2


async def test_missing_system_returns_none(db: aiosqlite.Connection):
    assert await get_latest_snapshot(db, system="codex") is None


async def test_unknown_agent_rejected(db: aiosqlite.Connection):
    with pytest.raises(ValueError, match="Unknown agent"):
        await save_snapshot(db, caller="nope", data={})


async def test_retention_and_fts(db: aiosqlite.Connection, monkeypatch):
    monkeypatch.setattr(config, "SNAPSHOT_RETENTION_PER_SYSTEM", 2)
    for i in range(5):
        await save_snapshot(db, caller="codex", data={"i": i})
    cursor = await db.execute("SELECT COUNT(*) FROM snapshots")
    assert (await cursor.fetchone())[0] == 2
    metrics = await collect_fts_metrics(db)
    assert metrics["ok"] is True
    assert metrics["sources"]["snapshot"]["orphaned"] == 0
