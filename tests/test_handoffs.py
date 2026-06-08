from __future__ import annotations

import aiosqlite
import pytest

from agent_bridge.db import collect_fts_metrics
from agent_bridge.tools.handoffs import (
    clear_handoff,
    create_handoff,
    get_pending_handoffs,
    pick_up_handoff,
)


async def test_create_then_pending(db: aiosqlite.Connection):
    res = await create_handoff(db, caller="claude-ai", project="recall", phase="Phase 2")
    assert res["status"] == "pending"
    pending = await get_pending_handoffs(db)
    assert len(pending) == 1
    assert pending[0]["project"] == "recall"


async def test_full_lifecycle(db: aiosqlite.Connection):
    res = await create_handoff(db, caller="claude-ai", project="recall")
    hid = res["id"]
    picked = await pick_up_handoff(db, caller="codex", handoff_id=hid)
    assert picked["status"] == "active"
    assert picked["picked_up_by"] == "codex"
    cleared = await clear_handoff(db, caller="codex", project="recall")
    assert cleared["cleared"] == 1
    assert await get_pending_handoffs(db) == []


async def test_pickup_unknown_id(db: aiosqlite.Connection):
    with pytest.raises(ValueError, match="No handoff"):
        await pick_up_handoff(db, caller="codex", handoff_id=999)


async def test_cannot_pickup_active(db: aiosqlite.Connection):
    res = await create_handoff(db, caller="claude-ai", project="recall")
    await pick_up_handoff(db, caller="codex", handoff_id=res["id"])
    with pytest.raises(ValueError, match="not pending"):
        await pick_up_handoff(db, caller="claude-code", handoff_id=res["id"])


async def test_clear_nonexistent_is_noop(db: aiosqlite.Connection):
    res = await clear_handoff(db, caller="codex", project="ghost")
    assert res["cleared"] == 0


async def test_clear_preserves_fts_invariant(db: aiosqlite.Connection):
    res = await create_handoff(db, caller="claude-ai", project="recall")
    await clear_handoff(db, caller="codex", project="recall")
    metrics = await collect_fts_metrics(db)
    # Cleared handoff keeps its source row AND its FTS entry — invariant holds,
    # and the handoff stays searchable via recall.
    assert metrics["ok"] is True
    assert metrics["sources"]["handoff"]["indexed"] == 1
    assert metrics["sources"]["handoff"]["missing"] == 0
    assert res["id"] is not None


async def test_unknown_agent_rejected(db: aiosqlite.Connection):
    with pytest.raises(ValueError, match="Unknown agent"):
        await create_handoff(db, caller="rogue", project="x")
