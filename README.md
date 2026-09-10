# AgenticBridge

**A SQLite-backed MCP server that gives your AI coding agents a shared memory bus.**

PyPI distribution name: `AgenticBridge`. The Python module remains
`agent_bridge`, the installed CLI remains `agent-bridge`, and the source
repository remains `agent-bridge`.

You run more than one coding agent now. Maybe Claude Code in one terminal and Codex in another. Maybe a planner model in a chat window dispatching work to executors on your machine. The problem isn't the agents — it's that **none of them know what the others did.** Every session starts cold. Work gets redone. Handoffs happen by copy-paste.

`agent-bridge` is the missing shared state. It's a single [Model Context Protocol](https://modelcontextprotocol.io) server backed by one SQLite file, exposing a small set of tools that any MCP-speaking agent can call:

- **Context sections** — long-lived shared notes with single-writer ownership.
- **Activity log** — a rolling "what happened" feed across every agent.
- **Handoffs** — a dispatch queue: one agent assigns work, another picks it up, whoever finishes clears it.
- **Snapshots** — periodic per-agent state captures.
- **Recall** — one full-text (FTS5) search across all of the above.
- **Health / status** — observability over the bridge itself.

No server to host. No vector DB. No cloud. One file, one process, stdio transport.

---

## Why this exists

This is the genericized, open-source distillation of the coordination spine from a working one-person "AI operating system" — the piece that let a planning model, two terminal coding agents, and a few background jobs operate as a *team* instead of four amnesiacs. The original is personal; this is the reusable pattern, rebuilt clean with no machine-specific anything.

The design bet: **agents don't need a knowledge graph to coordinate. They need a shared scratchpad with ownership rules and good search.** Everything here serves that and stops there.

---

## Relationship to bridge-db

`agent-bridge` is the generic, reusable shared-state bus extracted from a more
opinionated local operating system. If you are working on the author's machine,
that production local spine is [`bridge-db`](https://github.com/saagpatel/bridge-db):
it adds machine-specific integrations such as principal/auth rollout, source
trust, Claude.ai file fallback sync, shipped-event receipts, Notion sync
contracts, cost records, audit logs, and richer observability.

Use `agent-bridge` when you want the portable core pattern: context sections,
activity, handoffs, snapshots, lexical recall, and health over one local SQLite
file. Do not register it as a second live bridge next to an existing `bridge-db`
deployment unless you intentionally want a separate, isolated state store.

---

## Install

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

From PyPI:

```bash
uvx --from AgenticBridge agent-bridge --status
```

From source:

```bash
git clone https://github.com/saagpatel/agent-bridge
cd agent-bridge
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Register it with any MCP client. For Claude Code:

```bash
claude mcp add --scope user agent-bridge -- uv run --directory /abs/path/to/agent-bridge python -m agent_bridge
```

For Claude Desktop / other clients, point them at the command `uv run --directory /abs/path/to/agent-bridge python -m agent_bridge` over stdio.

For Codex, add a stdio server block to `~/.codex/config.toml`:

```toml
[mcp_servers.agent-bridge]
command = "uv"
args = ["run", "--directory", "/abs/path/to/agent-bridge", "python", "-m", "agent_bridge"]
```

If this machine already has a production bridge such as `bridge-db`, keep
`agent-bridge` unregistered or point it at a deliberately separate test DB.
Running both against normal agent workflows will split coordination state.

---

## Release Notes

### 0.1.2

- Refresh locked transitive runtime dependencies flagged by Dependabot:
  `cryptography`, `starlette`, and the `mcp` SDK path that brings in
  Starlette.

---

## Configure (all optional)

Everything machine-specific is an environment variable. Defaults are sensible.

| Variable | Default | Purpose |
|---|---|---|
| `AGENT_BRIDGE_DB_PATH` | `~/.local/share/agent-bridge/bridge.db` | Where the SQLite file lives |
| `AGENT_BRIDGE_MARKDOWN_PATH` | next to the DB | Where the markdown mirror is written |
| `AGENT_BRIDGE_AGENTS` | `claude-code,codex,claude-ai,human` | Allowlist of agent identities that may write |
| `AGENT_BRIDGE_ACTIVITY_RETENTION` | `50` | Activity rows kept per agent |
| `AGENT_BRIDGE_SNAPSHOT_RETENTION` | `10` | Snapshots kept per agent |

Agent identities are **not** baked into the schema — set `AGENT_BRIDGE_AGENTS` to whatever your fleet is called (`cursor`, `aider`, `windsurf`, `human`, …).

---

## CLI

The same code runs as diagnostics without a live MCP client:

```bash
uv run python -m agent_bridge --status         # compact status JSON
uv run python -m agent_bridge --doctor         # environment + DB diagnostics
uv run python -m agent_bridge --export         # regenerate the markdown mirror
uv run python -m agent_bridge --rebuild-index  # repair FTS index drift
uv run python -m agent_bridge                  # start the MCP server (stdio)
```

---

## The tools

| Tool | What it does |
|---|---|
| `update_section` / `get_section` / `get_all_sections` | Owned context sections (first writer owns it) |
| `log_activity` / `get_recent_activity` | Append + read the cross-agent activity feed |
| `create_handoff` / `get_pending_handoffs` / `pick_up_handoff` / `clear_handoff` | The work-dispatch queue |
| `save_snapshot` / `get_latest_snapshot` | Per-agent state captures |
| `recall_search` | FTS5 search across everything |
| `export_markdown` | Render a human-readable mirror |
| `health` / `status` / `rebuild_index` | Observability + index repair |

---

## How it's built

The interesting parts are documented in [docs/architecture.md](docs/architecture.md), and the story of the system it came from is in [docs/one-person-ai-operating-system.md](docs/one-person-ai-operating-system.md). Three ideas carry the whole thing:

1. **One write path per table, FTS mirror updated in the same transaction.** This single invariant is what keeps search honest — there's no separate "reindex" step that can fall behind. `health` checks it; `rebuild_index` repairs it.
2. **Core logic is transport-free.** Every tool is a plain `async` function over a database connection. The MCP server is a thin wrapper. That's why the test suite never needs a live MCP client — it calls the functions directly.
3. **Ownership in the app layer, not the schema.** Agent identities are config, so the same schema serves any team without a migration.

---

## Scope (what this is *not*)

It is not a knowledge base, a vector store, or a RAG system. It's coordination state plus lexical search. That boundary is deliberate — the original system tried the knowledge-store path and walked it back when most "missed" searches turned out to be for content that was never in the bridge to begin with. If you need semantic memory, put it behind its own MCP server and let the agents call both.

---

## License

MIT — see [LICENSE](LICENSE).
