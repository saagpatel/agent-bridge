from __future__ import annotations

import aiosqlite
import pytest

from agent_bridge.db import (
    SCHEMA_VERSION,
    collect_fts_metrics,
    ensure_schema,
    insert_activity_row,
    open_db,
    repopulate_content_index,
)


async def test_fresh_schema_sets_version(db: aiosqlite.Connection):
    cursor = await db.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    assert row[0] == SCHEMA_VERSION


async def test_all_tables_exist(db: aiosqlite.Connection):
    cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in await cursor.fetchall()}
    assert {"context_sections", "activity_log", "snapshots", "handoffs"} <= tables


async def test_newer_schema_is_refused(tmp_path):
    path = tmp_path / "future.db"
    conn = await aiosqlite.connect(str(path))
    await conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    await conn.commit()
    with pytest.raises(RuntimeError, match="newer than this build"):
        await ensure_schema(conn)
    await conn.close()


async def test_fts_metrics_clean_on_empty(db: aiosqlite.Connection):
    metrics = await collect_fts_metrics(db)
    assert metrics["ok"] is True
    assert metrics["missing"] == 0
    assert metrics["orphaned"] == 0


async def test_insert_activity_keeps_fts_in_sync(db: aiosqlite.Connection):
    await insert_activity_row(
        db, source="codex", timestamp="2026-01-01", project="proj", summary="did a thing"
    )
    await db.commit()
    metrics = await collect_fts_metrics(db)
    assert metrics["ok"] is True
    assert metrics["sources"]["activity"]["indexed"] == 1


async def test_retention_prunes_and_gcs_fts(db: aiosqlite.Connection):
    for i in range(5):
        await insert_activity_row(
            db,
            source="codex",
            timestamp="2026-01-01",
            project="proj",
            summary=f"entry {i}",
            retention_limit=3,
        )
    await db.commit()
    cursor = await db.execute("SELECT COUNT(*) FROM activity_log")
    assert (await cursor.fetchone())[0] == 3
    # FTS must not retain rows for pruned activity.
    metrics = await collect_fts_metrics(db)
    assert metrics["ok"] is True
    assert metrics["sources"]["activity"]["orphaned"] == 0


async def test_repopulate_is_idempotent(db: aiosqlite.Connection):
    await insert_activity_row(db, source="codex", timestamp="2026-01-01", project="p", summary="s")
    await db.commit()
    first = await repopulate_content_index(db)
    second = await repopulate_content_index(db)
    assert first == second
    metrics = await collect_fts_metrics(db)
    assert metrics["ok"] is True


async def test_open_db_is_reentrant(tmp_path):
    path = tmp_path / "reopen.db"
    conn = await open_db(path)
    await conn.close()
    conn2 = await open_db(path)  # second open must not re-run DDL destructively
    cursor = await conn2.execute("PRAGMA user_version")
    assert (await cursor.fetchone())[0] == SCHEMA_VERSION
    await conn2.close()
