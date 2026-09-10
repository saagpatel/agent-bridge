"""Schema, connection setup, and the FTS5 content-index invariant.

Design notes
------------
* **One write path per table.** Every mutation to an indexable table goes through
  a helper here that also updates the `content_index` FTS5 mirror in the same
  transaction. This is the single invariant that keeps `recall` honest.
* **Agent identity is not in the schema.** Columns that hold an agent id are plain
  TEXT; validation happens in the app layer against the configured allowlist
  (see config.py). That is what lets the same schema serve any team.
* **Step-wise migrations.** `ensure_schema` advances `PRAGMA user_version` one step
  at a time and commits after each, so a crash mid-upgrade leaves the DB at the
  last fully-migrated version. v1 is the initial release; the loop is where future
  migrations slot in.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("agent_bridge.db")

SCHEMA_VERSION = 1

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS context_sections (
    section_name TEXT PRIMARY KEY,
    owner        TEXT NOT NULL,
    content      TEXT NOT NULL DEFAULT '',
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS activity_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL,
    timestamp  TEXT NOT NULL,
    project    TEXT NOT NULL,
    summary    TEXT NOT NULL,
    branch     TEXT,
    tags       TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_activity_source ON activity_log(source);
CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON activity_log(timestamp DESC);

CREATE TABLE IF NOT EXISTS snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    system        TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    data          TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_snapshot_system ON snapshots(system, created_at DESC);

CREATE TABLE IF NOT EXISTS handoffs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project       TEXT NOT NULL,
    project_path  TEXT,
    roadmap_file  TEXT,
    phase         TEXT,
    dispatched_by TEXT NOT NULL,
    dispatched_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    picked_up_by  TEXT,
    picked_up_at  TEXT,
    cleared_at    TEXT,
    status        TEXT NOT NULL DEFAULT 'pending'
                  CHECK(status IN ('pending', 'active', 'cleared'))
);
CREATE INDEX IF NOT EXISTS idx_handoff_status ON handoffs(status);

CREATE VIRTUAL TABLE IF NOT EXISTS content_index USING fts5(
    source_type UNINDEXED,
    source_id   UNINDEXED,
    text,
    tokenize = 'porter unicode61 remove_diacritics 2'
);
"""

# Primary-key map used by the FTS garbage collector and consistency metrics.
_FTS_SOURCE_TABLES: dict[str, tuple[str, str]] = {
    "section": ("context_sections", "section_name"),
    "activity": ("activity_log", "id"),
    "snapshot": ("snapshots", "id"),
    "handoff": ("handoffs", "id"),
}


async def apply_pragmas(db: aiosqlite.Connection) -> None:
    """Apply required PRAGMAs. Safe on every open."""
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.execute("PRAGMA busy_timeout=5000")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.commit()


async def ensure_schema(db: aiosqlite.Connection) -> None:
    """Create the schema on a fresh DB, or step migrations forward."""
    cursor = await db.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    version: int = row[0] if row else 0

    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"Database schema is newer than this build supports "
            f"(db=v{version}, supported=v{SCHEMA_VERSION}). Upgrade agent-bridge."
        )

    if version == 0:
        logger.info("Initializing fresh schema v%d", SCHEMA_VERSION)
        await db.executescript(_SCHEMA_DDL)
        await db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        await db.commit()
        return

    # Future migrations slot in here, one step per version:
    #   while version < SCHEMA_VERSION:
    #       if version == 1: ...; version = 2; commit
    while version < SCHEMA_VERSION:  # pragma: no cover - no migrations past v1 yet
        raise RuntimeError(f"No migration path defined from v{version}")


async def open_db(path: Path) -> aiosqlite.Connection:
    """Open a connection with pragmas + schema applied. Caller closes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(str(path))
    db.row_factory = aiosqlite.Row
    await apply_pragmas(db)
    await ensure_schema(db)
    return db


# ── FTS5 content-index helpers ────────────────────────────────────────────────
# These stage writes only; the calling tool commits so index + source land in one
# transaction.


def fts_text_for_section(section_name: str, content: str) -> str:
    return f"{section_name}\n{content}"


def fts_text_for_activity(project: str, summary: str, branch: str | None) -> str:
    parts = [project, summary]
    if branch:
        parts.append(branch)
    return "\n".join(parts)


def fts_text_for_snapshot(data: str) -> str:
    return data


def fts_text_for_handoff(
    project: str, project_path: str | None, roadmap_file: str | None, phase: str | None
) -> str:
    parts = [project]
    parts.extend(p for p in (project_path, roadmap_file, phase) if p)
    return "\n".join(parts)


async def upsert_fts_entry(
    db: aiosqlite.Connection, source_type: str, source_id: str, text: str
) -> None:
    """Replace the content_index row for a source key (delete + insert)."""
    await db.execute(
        "DELETE FROM content_index WHERE source_type = ? AND source_id = ?",
        (source_type, source_id),
    )
    await db.execute(
        "INSERT INTO content_index (source_type, source_id, text) VALUES (?, ?, ?)",
        (source_type, source_id, text),
    )


async def delete_fts_entry(db: aiosqlite.Connection, source_type: str, source_id: str) -> None:
    await db.execute(
        "DELETE FROM content_index WHERE source_type = ? AND source_id = ?",
        (source_type, source_id),
    )


async def gc_fts_orphans(db: aiosqlite.Connection, source_type: str) -> int:
    """Drop index rows whose source row no longer exists. Returns rows removed."""
    if source_type not in _FTS_SOURCE_TABLES:
        raise ValueError(f"Unknown source_type for GC: {source_type}")
    table, pk = _FTS_SOURCE_TABLES[source_type]
    cursor = await db.execute(
        f"""
        DELETE FROM content_index
        WHERE source_type = ?
          AND source_id NOT IN (SELECT CAST({pk} AS TEXT) FROM {table})
        """,  # noqa: S608 - table/pk come from a closed literal map
        (source_type,),
    )
    return cursor.rowcount or 0


async def insert_activity_row(
    db: aiosqlite.Connection,
    *,
    source: str,
    timestamp: str,
    project: str,
    summary: str,
    branch: str | None = None,
    tags: list[str] | None = None,
    retention_limit: int | None = None,
) -> int:
    """Insert an activity row, keep the FTS mirror in sync, prune to retention."""
    cursor = await db.execute(
        """
        INSERT INTO activity_log (source, timestamp, project, summary, branch, tags)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (source, timestamp, project, summary, branch, json.dumps(tags or [])),
    )
    activity_id = cursor.lastrowid
    if activity_id is None:
        raise RuntimeError("activity_log insert did not return an id")

    await upsert_fts_entry(
        db, "activity", str(activity_id), fts_text_for_activity(project, summary, branch)
    )

    if retention_limit is not None:
        await db.execute(
            """
            DELETE FROM activity_log
            WHERE source = ? AND id NOT IN (
                SELECT id FROM activity_log WHERE source = ?
                ORDER BY created_at DESC, id DESC LIMIT ?
            )
            """,
            (source, source, retention_limit),
        )
        await gc_fts_orphans(db, "activity")

    return int(activity_id)


async def collect_fts_metrics(db: aiosqlite.Connection) -> dict[str, Any]:
    """Source-vs-index consistency metrics, the heart of the health check."""
    sources: dict[str, dict[str, int | bool]] = {}
    totals = {"expected": 0, "indexed": 0, "missing": 0, "orphaned": 0}

    for source_type, (table, pk) in _FTS_SOURCE_TABLES.items():
        expected = await _scalar(db, f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        indexed = await _scalar(
            db, "SELECT COUNT(*) FROM content_index WHERE source_type = ?", (source_type,)
        )
        missing = await _scalar(
            db,
            f"""
            SELECT COUNT(*) FROM {table} AS s
            WHERE NOT EXISTS (
                SELECT 1 FROM content_index i
                WHERE i.source_type = ? AND i.source_id = CAST(s.{pk} AS TEXT)
            )
            """,  # noqa: S608
            (source_type,),
        )
        orphaned = await _scalar(
            db,
            f"""
            SELECT COUNT(*) FROM content_index i
            WHERE i.source_type = ?
              AND NOT EXISTS (
                  SELECT 1 FROM {table} s WHERE CAST(s.{pk} AS TEXT) = i.source_id
              )
            """,  # noqa: S608
            (source_type,),
        )
        ok = expected == indexed and missing == 0 and orphaned == 0
        sources[source_type] = {
            "expected": expected,
            "indexed": indexed,
            "missing": missing,
            "orphaned": orphaned,
            "ok": ok,
        }
        for k in totals:
            totals[k] += sources[source_type][k]  # type: ignore[index]

    return {"ok": all(s["ok"] for s in sources.values()), **totals, "sources": sources}


async def repopulate_content_index(db: aiosqlite.Connection) -> dict[str, int]:
    """Rebuild content_index from all source tables. Idempotent."""
    await db.execute("DELETE FROM content_index")
    counts = {"section": 0, "activity": 0, "snapshot": 0, "handoff": 0}

    async for row in await db.execute("SELECT section_name, content FROM context_sections"):
        await _index(
            db,
            "section",
            row["section_name"],
            fts_text_for_section(row["section_name"], row["content"]),
        )
        counts["section"] += 1

    async for row in await db.execute("SELECT id, project, summary, branch FROM activity_log"):
        await _index(
            db,
            "activity",
            str(row["id"]),
            fts_text_for_activity(row["project"], row["summary"], row["branch"]),
        )
        counts["activity"] += 1

    async for row in await db.execute("SELECT id, data FROM snapshots"):
        await _index(db, "snapshot", str(row["id"]), fts_text_for_snapshot(row["data"]))
        counts["snapshot"] += 1

    async for row in await db.execute(
        "SELECT id, project, project_path, roadmap_file, phase FROM handoffs"
    ):
        await _index(
            db,
            "handoff",
            str(row["id"]),
            fts_text_for_handoff(
                row["project"], row["project_path"], row["roadmap_file"], row["phase"]
            ),
        )
        counts["handoff"] += 1

    await db.commit()
    logger.info("content_index repopulated: %s", counts)
    return counts


async def _index(db: aiosqlite.Connection, source_type: str, source_id: str, text: str) -> None:
    await db.execute(
        "INSERT INTO content_index (source_type, source_id, text) VALUES (?, ?, ?)",
        (source_type, source_id, text),
    )


async def _scalar(db: aiosqlite.Connection, sql: str, params: tuple[Any, ...] = ()) -> int:
    cursor = await db.execute(sql, params)
    row = await cursor.fetchone()
    return int(row[0]) if row else 0
