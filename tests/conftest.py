from __future__ import annotations

from collections.abc import AsyncIterator

import aiosqlite
import pytest_asyncio

from agent_bridge.db import open_db


@pytest_asyncio.fixture
async def db(tmp_path) -> AsyncIterator[aiosqlite.Connection]:
    conn = await open_db(tmp_path / "test.db")
    try:
        yield conn
    finally:
        await conn.close()
