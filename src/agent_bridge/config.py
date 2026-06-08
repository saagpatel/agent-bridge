"""Runtime configuration for agent-bridge.

Everything that couples the bridge to a particular machine or team lives here and
is driven by environment variables, so the same code runs unchanged for any set
of agents. Defaults are deliberately generic.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Database location ─────────────────────────────────────────────────────────
# Override with AGENT_BRIDGE_DB_PATH. Defaults to an XDG-style data dir.


def db_path() -> Path:
    """Resolve the SQLite database path (env override → XDG default)."""
    override = os.environ.get("AGENT_BRIDGE_DB_PATH")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "agent-bridge" / "bridge.db"


# ── Markdown export location ──────────────────────────────────────────────────
# Where export_markdown writes the human-readable mirror. Override with
# AGENT_BRIDGE_MARKDOWN_PATH.


def markdown_path() -> Path:
    """Resolve the markdown export path (env override → next to the DB)."""
    override = os.environ.get("AGENT_BRIDGE_MARKDOWN_PATH")
    if override:
        return Path(override).expanduser()
    return db_path().parent / "bridge.md"


# ── Agent identities ──────────────────────────────────────────────────────────
# The set of agents allowed to write. Override with AGENT_BRIDGE_AGENTS as a
# comma-separated list, e.g. "claude-code,codex,cursor,human". Ownership and
# write-access checks validate the `caller`/`source` against this allowlist —
# there is no hardcoded identity baked into the schema.

_DEFAULT_AGENTS = ("claude-code", "codex", "claude-ai", "human")


def agents() -> tuple[str, ...]:
    """Resolve the allowlist of agent identities (env override → defaults)."""
    raw = os.environ.get("AGENT_BRIDGE_AGENTS")
    if not raw:
        return _DEFAULT_AGENTS
    parsed = tuple(a.strip() for a in raw.split(",") if a.strip())
    return parsed or _DEFAULT_AGENTS


def is_known_agent(agent: str) -> bool:
    """True if `agent` is in the configured allowlist."""
    return agent in agents()


# ── Retention ─────────────────────────────────────────────────────────────────
# Activity rows are pruned per-source; snapshots per-system. Keeps the bridge a
# rolling working set, not an append-only ledger.

ACTIVITY_RETENTION_PER_SOURCE = int(os.environ.get("AGENT_BRIDGE_ACTIVITY_RETENTION", "50"))
SNAPSHOT_RETENTION_PER_SYSTEM = int(os.environ.get("AGENT_BRIDGE_SNAPSHOT_RETENTION", "10"))
