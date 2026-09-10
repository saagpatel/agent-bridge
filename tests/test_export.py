from __future__ import annotations

import aiosqlite

from agent_bridge.tools.activity import log_activity
from agent_bridge.tools.context import update_section
from agent_bridge.tools.export import export_markdown, render_markdown
from agent_bridge.tools.handoffs import create_handoff


async def test_render_includes_all_sections(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="roadmap", content="ship it")
    await log_activity(db, caller="codex", project="proj", summary="did work")
    await create_handoff(db, caller="claude-ai", project="proj", phase="Phase 1")
    md = await render_markdown(db)
    assert "# agent-bridge" in md
    assert "roadmap" in md
    assert "ship it" in md
    assert "did work" in md
    assert "Phase 1" in md


async def test_render_empty_state(db: aiosqlite.Connection):
    md = await render_markdown(db)
    assert "_No sections yet._" in md
    assert "_None._" in md


async def test_export_writes_file(db: aiosqlite.Connection, tmp_path):
    target = tmp_path / "out" / "bridge.md"
    result = await export_markdown(db, path=target)
    assert target.exists()
    assert result["path"] == str(target)
    assert int(result["bytes"]) > 0
