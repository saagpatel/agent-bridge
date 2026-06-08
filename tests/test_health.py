from __future__ import annotations

import aiosqlite

from agent_bridge.tools.activity import log_activity
from agent_bridge.tools.handoffs import create_handoff
from agent_bridge.tools.health import health, status


async def test_health_clean_on_empty(db: aiosqlite.Connection):
    report = await health(db)
    assert report["ok"] is True
    assert report["schema_version"] >= 1
    assert report["counts"]["activity"] == 0


async def test_health_counts(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="s")
    await create_handoff(db, caller="claude-ai", project="p")
    report = await health(db)
    assert report["counts"]["activity"] == 1
    assert report["counts"]["handoffs"] == 1
    assert report["pending_handoffs"] == 1
    assert report["fts_index"]["ok"] is True


async def test_status_detects_drift(db: aiosqlite.Connection):
    await log_activity(db, caller="codex", project="p", summary="s")
    # Manually corrupt the index to simulate drift.
    await db.execute("DELETE FROM content_index WHERE source_type = 'activity'")
    await db.commit()
    st = await status(db)
    assert st["fts_drift"] is True
    assert st["fts_missing"] == 1
    assert st["ok"] is False
