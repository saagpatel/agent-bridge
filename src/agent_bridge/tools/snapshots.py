"""Snapshots — periodic system-state captures per agent.

A snapshot is an opaque JSON blob (active projects, lessons, open threads —
whatever an agent wants to persist between sessions). Retained as a rolling
window per system so the bridge keeps recent state without unbounded growth.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from .. import config
from ..db import fts_text_for_snapshot, gc_fts_orphans, upsert_fts_entry


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


async def save_snapshot(
    db: aiosqlite.Connection,
    *,
    caller: str,
    data: dict[str, Any],
    snapshot_date: str | None = None,
) -> dict[str, Any]:
    """Save a system-state snapshot. Prunes to the per-system retention limit."""
    if not config.is_known_agent(caller):
        raise ValueError(f"Unknown agent: {caller!r}. Allowed: {', '.join(config.agents())}")

    payload = json.dumps(data)
    cursor = await db.execute(
        "INSERT INTO snapshots (system, snapshot_date, data) VALUES (?, ?, ?)",
        (caller, snapshot_date or _today(), payload),
    )
    snapshot_id = cursor.lastrowid
    if snapshot_id is None:
        raise RuntimeError("snapshots insert did not return an id")
    await upsert_fts_entry(db, "snapshot", str(snapshot_id), fts_text_for_snapshot(payload))

    await db.execute(
        """
        DELETE FROM snapshots
        WHERE system = ? AND id NOT IN (
            SELECT id FROM snapshots WHERE system = ?
            ORDER BY created_at DESC, id DESC LIMIT ?
        )
        """,
        (caller, caller, config.SNAPSHOT_RETENTION_PER_SYSTEM),
    )
    await gc_fts_orphans(db, "snapshot")
    await db.commit()
    return {"id": int(snapshot_id), "system": caller, "ok": True}


async def get_latest_snapshot(db: aiosqlite.Connection, *, system: str) -> dict[str, Any] | None:
    """Return the most recent snapshot for a system, or None."""
    cursor = await db.execute(
        """
        SELECT id, system, snapshot_date, data, created_at
        FROM snapshots
        WHERE system = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        (system,),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    entry = dict(row)
    entry["data"] = json.loads(entry["data"])
    return entry
