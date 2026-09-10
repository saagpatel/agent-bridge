from __future__ import annotations

import aiosqlite
import pytest

from agent_bridge.tools.context import get_all_sections, get_section, update_section


async def test_create_and_read_section(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="roadmap", content="ship it")
    sec = await get_section(db, "roadmap")
    assert sec is not None
    assert sec["owner"] == "claude-ai"
    assert sec["content"] == "ship it"


async def test_owner_can_update_own_section(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="roadmap", content="v1")
    await update_section(db, caller="claude-ai", section_name="roadmap", content="v2")
    sec = await get_section(db, "roadmap")
    assert sec["content"] == "v2"


async def test_non_owner_cannot_overwrite(db: aiosqlite.Connection):
    await update_section(db, caller="claude-ai", section_name="roadmap", content="mine")
    with pytest.raises(PermissionError):
        await update_section(db, caller="codex", section_name="roadmap", content="hijack")
    sec = await get_section(db, "roadmap")
    assert sec["content"] == "mine"


async def test_unknown_agent_rejected(db: aiosqlite.Connection):
    with pytest.raises(ValueError, match="Unknown agent"):
        await update_section(db, caller="rogue-bot", section_name="x", content="y")


async def test_get_missing_section_returns_none(db: aiosqlite.Connection):
    assert await get_section(db, "nope") is None


async def test_get_all_sections(db: aiosqlite.Connection):
    await update_section(db, caller="codex", section_name="a", content="1")
    await update_section(db, caller="codex", section_name="b", content="2")
    allsec = await get_all_sections(db)
    assert set(allsec) == {"a", "b"}
