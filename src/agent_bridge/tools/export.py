"""export_markdown — regenerate a human-readable mirror of the bridge.

A SQLite DB is great for agents and terrible for humans skimming on their phone.
This renders the current state to a single markdown file so any file-based client
(or a person) can read it without an MCP connection. The DB stays the source of
truth; the markdown is a derived view.
"""

from __future__ import annotations

import json
from pathlib import Path

import aiosqlite

from .. import config
from .activity import get_recent_activity
from .context import get_all_sections
from .handoffs import get_pending_handoffs


async def render_markdown(db: aiosqlite.Connection) -> str:
    """Render the current bridge state to markdown text."""
    lines: list[str] = ["# agent-bridge", ""]

    sections = await get_all_sections(db)
    lines.append("## Context Sections")
    lines.append("")
    if not sections:
        lines.append("_No sections yet._")
    for name, sec in sections.items():
        lines.append(f"### {name}")
        lines.append(f"_owner: {sec['owner']} · updated: {sec['updated_at']}_")
        lines.append("")
        lines.append(sec["content"] or "_(empty)_")
        lines.append("")

    handoffs = await get_pending_handoffs(db)
    lines.append("## Open Handoffs")
    lines.append("")
    if not handoffs:
        lines.append("_None._")
    for h in handoffs:
        owner = h["picked_up_by"] or "unclaimed"
        lines.append(
            f"- **{h['project']}** ({h['status']}, {owner}) "
            f"— dispatched by {h['dispatched_by']}"
            + (f", phase {h['phase']}" if h["phase"] else "")
        )
    lines.append("")

    activity = await get_recent_activity(db, limit=20)
    lines.append("## Recent Activity")
    lines.append("")
    if not activity:
        lines.append("_None._")
    for a in activity:
        tag_str = f" {json.dumps(a['tags'])}" if a["tags"] else ""
        lines.append(
            f"- `{a['timestamp']}` **{a['source']}** / {a['project']}: {a['summary']}{tag_str}"
        )
    lines.append("")

    return "\n".join(lines)


async def export_markdown(db: aiosqlite.Connection, *, path: Path | None = None) -> dict[str, str]:
    """Render and write the markdown mirror. Returns the path written."""
    target = path or config.markdown_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    content = await render_markdown(db)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "bytes": str(len(content.encode("utf-8")))}
