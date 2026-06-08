"""MCP server: binds the core tool functions to stdio MCP endpoints.

The core logic lives in tools/* as plain async functions over a db connection.
This module is the thin transport layer — a lifespan that owns the connection,
plus one wrapper per tool. Keeping them separate is what makes the core unit-
testable without a live MCP client.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import aiosqlite
from mcp.server.fastmcp import Context, FastMCP

from . import config
from .db import open_db, repopulate_content_index
from .tools import activity, context, export, handoffs, recall, snapshots
from .tools import health as health_tools

# JSON-RPC owns stdout; all logging must go to stderr.
logging.basicConfig(stream=sys.stderr, level=logging.INFO)


@dataclass
class AppContext:
    db: aiosqlite.Connection


@asynccontextmanager
async def lifespan(_server: FastMCP) -> AsyncIterator[AppContext]:
    db = await open_db(config.db_path())
    try:
        yield AppContext(db=db)
    finally:
        await db.close()


mcp = FastMCP("agent-bridge", lifespan=lifespan)


def _db(ctx: Context) -> aiosqlite.Connection:
    return ctx.request_context.lifespan_context.db


# ── context sections ──────────────────────────────────────────────────────────
@mcp.tool()
async def update_section(caller: str, section_name: str, content: str, ctx: Context) -> dict:
    """Create or update an owned context section (first-writer ownership)."""
    return await context.update_section(
        _db(ctx), caller=caller, section_name=section_name, content=content
    )


@mcp.tool()
async def get_section(section_name: str, ctx: Context) -> dict | None:
    """Return one context section, or null if absent."""
    return await context.get_section(_db(ctx), section_name)


@mcp.tool()
async def get_all_sections(ctx: Context) -> dict:
    """Return all context sections keyed by name."""
    return await context.get_all_sections(_db(ctx))


# ── activity ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def log_activity(
    caller: str,
    project: str,
    summary: str,
    ctx: Context,
    branch: str | None = None,
    tags: list[str] | None = None,
    timestamp: str | None = None,
) -> dict:
    """Log a one-line activity entry (pruned to a rolling window per agent)."""
    return await activity.log_activity(
        _db(ctx),
        caller=caller,
        project=project,
        summary=summary,
        branch=branch,
        tags=tags,
        timestamp=timestamp,
    )


@mcp.tool()
async def get_recent_activity(
    ctx: Context, limit: int = 20, source: str | None = None, since: str | None = None
) -> list[dict]:
    """Return recent activity, newest first, with optional source/since filters."""
    return await activity.get_recent_activity(_db(ctx), limit=limit, source=source, since=since)


# ── handoffs ──────────────────────────────────────────────────────────────────
@mcp.tool()
async def create_handoff(
    caller: str,
    project: str,
    ctx: Context,
    project_path: str | None = None,
    roadmap_file: str | None = None,
    phase: str | None = None,
) -> dict:
    """Dispatch a pending handoff (a unit of work) for another agent to pick up."""
    return await handoffs.create_handoff(
        _db(ctx),
        caller=caller,
        project=project,
        project_path=project_path,
        roadmap_file=roadmap_file,
        phase=phase,
    )


@mcp.tool()
async def get_pending_handoffs(ctx: Context) -> list[dict]:
    """Return pending and active handoffs, newest first."""
    return await handoffs.get_pending_handoffs(_db(ctx))


@mcp.tool()
async def pick_up_handoff(caller: str, handoff_id: int, ctx: Context) -> dict:
    """Claim a pending handoff (pending -> active)."""
    return await handoffs.pick_up_handoff(_db(ctx), caller=caller, handoff_id=handoff_id)


@mcp.tool()
async def clear_handoff(caller: str, project: str, ctx: Context) -> dict:
    """Mark a project's open handoffs as cleared (done)."""
    return await handoffs.clear_handoff(_db(ctx), caller=caller, project=project)


# ── snapshots ─────────────────────────────────────────────────────────────────
@mcp.tool()
async def save_snapshot(
    caller: str, data: dict, ctx: Context, snapshot_date: str | None = None
) -> dict:
    """Save a system-state snapshot (rolling window per agent)."""
    return await snapshots.save_snapshot(
        _db(ctx), caller=caller, data=data, snapshot_date=snapshot_date
    )


@mcp.tool()
async def get_latest_snapshot(system: str, ctx: Context) -> dict | None:
    """Return the most recent snapshot for a system, or null."""
    return await snapshots.get_latest_snapshot(_db(ctx), system=system)


# ── recall + export + health ──────────────────────────────────────────────────
@mcp.tool()
async def recall_search(
    query: str, ctx: Context, limit: int = 10, scope: str = "all"
) -> list[dict]:
    """Lexical FTS5 search across sections, activity, snapshots, and handoffs."""
    return await recall.recall(_db(ctx), query=query, limit=limit, scope=scope)


@mcp.tool()
async def export_markdown(ctx: Context) -> dict:
    """Regenerate the human-readable markdown mirror of the bridge."""
    return await export.export_markdown(_db(ctx))


@mcp.tool()
async def health(ctx: Context) -> dict[str, Any]:
    """Full health report (row counts, FTS consistency, schema version)."""
    return await health_tools.health(_db(ctx))


@mcp.tool()
async def status(ctx: Context) -> dict[str, Any]:
    """Compact operator-facing status summary."""
    return await health_tools.status(_db(ctx))


@mcp.tool()
async def rebuild_index(ctx: Context) -> dict:
    """Rebuild the FTS content index from source tables (drift repair)."""
    counts = await repopulate_content_index(_db(ctx))
    return {"rebuilt": counts, "ok": True}


def run() -> None:
    """Start the MCP server over stdio."""
    mcp.run()
