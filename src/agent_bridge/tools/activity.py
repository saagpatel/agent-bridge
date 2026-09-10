"""Activity log — the shared "what happened" feed across agents.

Each agent logs one-line summaries of what it did. Rows are pruned to a rolling
window per source so the log stays a working set, not an archive. Every write
keeps the FTS mirror in sync via insert_activity_row.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import aiosqlite

from .. import config
from ..db import insert_activity_row


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


async def log_activity(
    db: aiosqlite.Connection,
    *,
    caller: str,
    project: str,
    summary: str,
    branch: str | None = None,
    tags: list[str] | None = None,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Record a one-line activity entry. Prunes to the per-source retention limit."""
    if not config.is_known_agent(caller):
        raise ValueError(f"Unknown agent: {caller!r}. Allowed: {', '.join(config.agents())}")

    activity_id = await insert_activity_row(
        db,
        source=caller,
        timestamp=timestamp or _today(),
        project=project,
        summary=summary,
        branch=branch,
        tags=tags,
        retention_limit=config.ACTIVITY_RETENTION_PER_SOURCE,
    )
    await db.commit()
    return {"id": activity_id, "source": caller, "project": project, "ok": True}


async def get_recent_activity(
    db: aiosqlite.Connection,
    *,
    limit: int = 20,
    source: str | None = None,
    since: str | None = None,
) -> list[dict[str, Any]]:
    """Return recent activity entries, newest first, with optional filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if source:
        clauses.append("source = ?")
        params.append(source)
    if since:
        clauses.append("timestamp >= ?")
        params.append(since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)

    cursor = await db.execute(
        f"""
        SELECT id, source, timestamp, project, summary, branch, tags, created_at
        FROM activity_log
        {where}
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,  # noqa: S608 - where clause built from a closed set of literals
        params,
    )
    rows = await cursor.fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        entry = dict(row)
        entry["tags"] = json.loads(entry["tags"])
        out.append(entry)
    return out
