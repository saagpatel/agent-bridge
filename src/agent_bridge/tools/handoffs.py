"""Handoffs — the work-dispatch queue between agents.

The coordination primitive: one agent (a planner) dispatches a unit of work; an
executor agent picks it up; whoever finishes clears it. A handoff moves
pending -> active -> cleared. This is what turns "several agents" into "a team".
"""

from __future__ import annotations

from typing import Any

import aiosqlite

from .. import config
from ..db import fts_text_for_handoff, upsert_fts_entry


async def create_handoff(
    db: aiosqlite.Connection,
    *,
    caller: str,
    project: str,
    project_path: str | None = None,
    roadmap_file: str | None = None,
    phase: str | None = None,
) -> dict[str, Any]:
    """Dispatch a new pending handoff."""
    if not config.is_known_agent(caller):
        raise ValueError(f"Unknown agent: {caller!r}. Allowed: {', '.join(config.agents())}")

    cursor = await db.execute(
        """
        INSERT INTO handoffs (project, project_path, roadmap_file, phase, dispatched_by)
        VALUES (?, ?, ?, ?, ?)
        """,
        (project, project_path, roadmap_file, phase, caller),
    )
    handoff_id = cursor.lastrowid
    if handoff_id is None:
        raise RuntimeError("handoffs insert did not return an id")
    await upsert_fts_entry(
        db,
        "handoff",
        str(handoff_id),
        fts_text_for_handoff(project, project_path, roadmap_file, phase),
    )
    await db.commit()
    return {"id": int(handoff_id), "project": project, "status": "pending", "ok": True}


async def get_pending_handoffs(db: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Return pending + active handoffs, newest first."""
    cursor = await db.execute(
        """
        SELECT id, project, project_path, roadmap_file, phase,
               dispatched_by, dispatched_at, picked_up_by, picked_up_at, status
        FROM handoffs
        WHERE status IN ('pending', 'active')
        ORDER BY dispatched_at DESC, id DESC
        """
    )
    return [dict(row) for row in await cursor.fetchall()]


async def pick_up_handoff(
    db: aiosqlite.Connection, *, caller: str, handoff_id: int
) -> dict[str, Any]:
    """Mark a pending handoff as active, claimed by `caller`."""
    if not config.is_known_agent(caller):
        raise ValueError(f"Unknown agent: {caller!r}. Allowed: {', '.join(config.agents())}")

    cursor = await db.execute("SELECT status FROM handoffs WHERE id = ?", (handoff_id,))
    row = await cursor.fetchone()
    if row is None:
        raise ValueError(f"No handoff with id {handoff_id}")
    if row["status"] != "pending":
        raise ValueError(f"Handoff {handoff_id} is {row['status']}, not pending")

    await db.execute(
        """
        UPDATE handoffs
        SET status = 'active',
            picked_up_by = ?,
            picked_up_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE id = ?
        """,
        (caller, handoff_id),
    )
    await db.commit()
    return {"id": handoff_id, "status": "active", "picked_up_by": caller, "ok": True}


async def clear_handoff(db: aiosqlite.Connection, *, caller: str, project: str) -> dict[str, Any]:
    """Mark all open handoffs for a project as cleared (done)."""
    if not config.is_known_agent(caller):
        raise ValueError(f"Unknown agent: {caller!r}. Allowed: {', '.join(config.agents())}")

    cursor = await db.execute(
        "SELECT id FROM handoffs WHERE project = ? AND status IN ('pending', 'active')",
        (project,),
    )
    ids = [row["id"] for row in await cursor.fetchall()]
    if not ids:
        return {"project": project, "cleared": 0, "ok": True}

    await db.execute(
        """
        UPDATE handoffs
        SET status = 'cleared',
            cleared_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
        WHERE project = ? AND status IN ('pending', 'active')
        """,
        (project,),
    )
    # FTS entries are kept: cleared handoffs stay part of the searchable record,
    # and the source row still exists, so the FTS invariant holds.
    await db.commit()
    return {"project": project, "cleared": len(ids), "ok": True}
