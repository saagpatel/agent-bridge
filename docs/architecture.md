# Architecture

`agent-bridge` is intentionally small. This document covers the few design
decisions that are worth understanding before you extend it.

## The shape

```
  any MCP client (Claude Code, Codex, Claude Desktop, Cursor, a script…)
                              │  stdio (JSON-RPC)
                              ▼
            ┌──────────────────────────────────┐
            │  agent_bridge.server (FastMCP)    │  ← thin transport wrapper
            │   one @mcp.tool() per endpoint    │
            └──────────────────────────────────┘
                              │  plain async calls
                              ▼
            ┌──────────────────────────────────┐
            │  agent_bridge.tools.*             │  ← all the logic, transport-free
            │   functions over a db connection  │
            └──────────────────────────────────┘
                              │
                              ▼
            ┌──────────────────────────────────┐
            │  SQLite (WAL)  +  FTS5 index      │
            └──────────────────────────────────┘
```

## Decision 1 — Core logic is transport-free

Every tool is a plain `async def f(db, *, ...) -> dict`. The MCP server
(`server.py`) is the *only* file that imports the `mcp` SDK; it does nothing but
pull the connection out of the lifespan context and call the core function.

Why it matters:

- **Tests never need a live MCP client.** `tests/` call the core functions
  directly with a real in-`tmp_path` SQLite connection. The suite is fast and
  has no transport flakiness.
- **The diagnostics CLI reuses the same functions.** `--status`, `--doctor`,
  `--export`, and `--rebuild-index` are just the core functions run under
  `asyncio.run`, with the `mcp` import deferred so diagnostics work even in an
  environment where the SDK isn't importable.
- **You could bolt on a second transport** (HTTP, a CLI subcommand per tool)
  without touching the logic.

## Decision 2 — One write path per table, FTS updated in the same transaction

The FTS5 `content_index` table mirrors the text of every row in
`context_sections`, `activity_log`, `snapshots`, and `handoffs`. The rule that
keeps it honest:

> Every function that mutates an indexable table updates the FTS mirror **in the
> same transaction**, via the helpers in `db.py` (`upsert_fts_entry`,
> `gc_fts_orphans`, `insert_activity_row`).

There is no background reindexer that can fall behind. If the index and the
source tables ever disagree, that's a bug, and:

- `health` / `status` report it as `fts_missing` (source row, no index entry) or
  `fts_orphaned` (index entry, no source row), and flip `ok` to `False`.
- `rebuild_index` (`repopulate_content_index`) repairs it by rebuilding the
  index from the source tables. It's idempotent.

`collect_fts_metrics` in `db.py` is the single source of truth for this check;
both `health` and the tests use it.

## Decision 3 — Ownership is config, not schema

The original system this is distilled from hardcoded its agent identities into
SQL `CHECK` constraints. That couples the schema to one machine and forces a
migration to add an agent.

Here, identity columns are plain `TEXT`. The allowlist lives in `config.py`
(`AGENT_BRIDGE_AGENTS`), and write tools validate the caller against it in the
app layer. Section ownership is *first-writer-wins*: whoever creates a section
owns it, and only the owner can update it. No static owner map, no migration to
onboard a new agent.

## Decision 4 — Retention keeps it a working set

Activity is pruned to `AGENT_BRIDGE_ACTIVITY_RETENTION` rows per source;
snapshots to `AGENT_BRIDGE_SNAPSHOT_RETENTION` per system. Pruning runs inside
the write path and garbage-collects the corresponding FTS rows, so the invariant
above survives retention. The bridge is a rolling coordination scratchpad, not
an append-only audit ledger.

## Decision 5 — Step-wise migrations

`ensure_schema` reads `PRAGMA user_version`, refuses to open a DB newer than the
build supports, and (when migrations exist) advances one version at a time,
committing after each step so a crash mid-upgrade leaves the DB at the last
fully-migrated version. v1 is the initial release; the migration loop is in place
for when the schema grows.

## Adding a new tool

1. Write the logic as an `async` function over `db` in a `tools/` module. If it
   touches an indexable table, call the FTS helper in the same transaction.
2. Add a thin `@mcp.tool()` wrapper in `server.py`.
3. Test the core function directly in `tests/` (no MCP needed).
4. If you added an indexable surface, extend `_FTS_SOURCE_TABLES` in `db.py` and
   `repopulate_content_index`.

## Deliberate non-goals

No embeddings, no vector search, no cross-machine sync, no auth beyond the
identity allowlist. The bridge coordinates agents on one machine and searches
its own state lexically. Anything more belongs behind its own MCP server.
