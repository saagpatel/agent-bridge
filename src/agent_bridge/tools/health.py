"""health / status — observability over the bridge itself.

`health` is the machine-readable diagnostic: row counts, FTS index consistency
(the one invariant that, if broken, silently degrades recall), and WAL size.
`status` is a compact operator-facing summary built on top of it.
"""

from __future__ import annotations

from typing import Any

import aiosqlite

from ..db import collect_fts_metrics


async def _count(db: aiosqlite.Connection, table: str) -> int:
    cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")  # noqa: S608 - fixed literals
    row = await cursor.fetchone()
    return int(row[0]) if row else 0


async def health(db: aiosqlite.Connection) -> dict[str, Any]:
    """Full health report. `ok` is False if any hard signal is failing."""
    counts = {
        "sections": await _count(db, "context_sections"),
        "activity": await _count(db, "activity_log"),
        "snapshots": await _count(db, "snapshots"),
        "handoffs": await _count(db, "handoffs"),
    }
    pending = await _count(db, "handoffs WHERE status IN ('pending', 'active')")
    fts = await collect_fts_metrics(db)

    cursor = await db.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    schema_version = int(row[0]) if row else 0

    # FTS drift is a hard failure: recall silently degrades if the index and the
    # source tables disagree.
    ok = bool(fts["ok"])
    return {
        "ok": ok,
        "schema_version": schema_version,
        "counts": counts,
        "pending_handoffs": pending,
        "fts_index": fts,
    }


async def status(db: aiosqlite.Connection) -> dict[str, Any]:
    """Compact operator summary."""
    report = await health(db)
    fts = report["fts_index"]
    return {
        "ok": report["ok"],
        "schema_version": report["schema_version"],
        "rows": sum(report["counts"].values()),
        "pending_handoffs": report["pending_handoffs"],
        "fts_drift": not fts["ok"],
        "fts_missing": fts["missing"],
        "fts_orphaned": fts["orphaned"],
    }
