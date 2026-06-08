"""recall — lexical FTS5 search across everything the bridge knows.

One query searches sections, activity, snapshots, and handoffs at once, ranked by
bm25. Multi-token queries use OR semantics (any token may match), and FTS5
operators in user input are stripped so a stray quote or "NEAR" can't blow up the
query.
"""

from __future__ import annotations

import re
from typing import Any

import aiosqlite

# Keep word characters only; everything else (quotes, parens, *, :, AND/OR/NEAR
# syntax) is replaced with spaces so user text is treated as plain terms.
_TOKEN_RE = re.compile(r"[^\w]+", re.UNICODE)

_VALID_SCOPES = ("all", "section", "activity", "snapshot", "handoff")


def _build_match_query(raw: str) -> str | None:
    """Turn free text into a safe FTS5 OR query, or None if nothing usable.

    Each token is double-quoted so FTS5 treats it as a literal term — this also
    neutralizes bare keyword tokens like AND/OR/NEAR that would otherwise be
    parsed as operators. Tokens are already word-chars only (punctuation split
    out above), so there are no embedded quotes to escape.
    """
    tokens = [t for t in _TOKEN_RE.split(raw) if t]
    if not tokens:
        return None
    return " OR ".join(f'"{t}"' for t in tokens)


async def recall(
    db: aiosqlite.Connection,
    *,
    query: str,
    limit: int = 10,
    scope: str = "all",
) -> list[dict[str, Any]]:
    """Search the content index. Returns ranked hits with a text snippet."""
    if scope not in _VALID_SCOPES:
        raise ValueError(f"Invalid scope {scope!r}. Allowed: {', '.join(_VALID_SCOPES)}")

    match = _build_match_query(query)
    if match is None:
        return []

    params: list[Any] = [match]
    scope_clause = ""
    if scope != "all":
        scope_clause = "AND source_type = ?"
        params.append(scope)
    params.append(limit)

    cursor = await db.execute(
        f"""
        SELECT source_type, source_id,
               snippet(content_index, 2, '[', ']', ' ... ', 16) AS snippet,
               bm25(content_index) AS rank
        FROM content_index
        WHERE content_index MATCH ?
        {scope_clause}
        ORDER BY rank
        LIMIT ?
        """,  # noqa: S608 - scope_clause is a fixed literal, value is parameterized
        params,
    )
    return [dict(row) for row in await cursor.fetchall()]
