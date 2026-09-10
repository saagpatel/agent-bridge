"""Owned context sections — long-lived shared state with single-writer ownership.

A section is claimed by the first agent that writes it; only that owner can
update it afterwards. This is how the bridge keeps, e.g., a "roadmap" section
authored by one agent from being clobbered by another.
"""

from __future__ import annotations

from typing import Any

import aiosqlite

from .. import config
from ..db import fts_text_for_section, upsert_fts_entry


async def update_section(
    db: aiosqlite.Connection, *, caller: str, section_name: str, content: str
) -> dict[str, Any]:
    """Create or update a section. Enforces first-writer ownership."""
    if not config.is_known_agent(caller):
        raise ValueError(f"Unknown agent: {caller!r}. Allowed: {', '.join(config.agents())}")

    cursor = await db.execute(
        "SELECT owner FROM context_sections WHERE section_name = ?", (section_name,)
    )
    existing = await cursor.fetchone()
    if existing is not None and existing["owner"] != caller:
        raise PermissionError(
            f"Section {section_name!r} is owned by {existing['owner']!r}; "
            f"{caller!r} cannot overwrite it."
        )

    await db.execute(
        """
        INSERT INTO context_sections (section_name, owner, content, updated_at)
        VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
        ON CONFLICT(section_name) DO UPDATE SET
            content = excluded.content,
            updated_at = excluded.updated_at
        """,
        (section_name, caller, content),
    )
    await upsert_fts_entry(db, "section", section_name, fts_text_for_section(section_name, content))
    await db.commit()
    return {"section_name": section_name, "owner": caller, "ok": True}


async def get_section(db: aiosqlite.Connection, section_name: str) -> dict[str, Any] | None:
    """Return one section, or None if it does not exist."""
    cursor = await db.execute(
        "SELECT section_name, owner, content, updated_at FROM context_sections "
        "WHERE section_name = ?",
        (section_name,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_sections(db: aiosqlite.Connection) -> dict[str, dict[str, Any]]:
    """Return every section keyed by name."""
    cursor = await db.execute(
        "SELECT section_name, owner, content, updated_at FROM context_sections "
        "ORDER BY section_name"
    )
    return {row["section_name"]: dict(row) for row in await cursor.fetchall()}
