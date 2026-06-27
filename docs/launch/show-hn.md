# Show HN draft

> Staged — do not post without operator review. Fill in the GitHub URL and your
> byline first. HN titles must be ≤ 80 chars and not editorialize.

## Title (pick one)

- `Show HN: Agent-bridge – a shared memory bus for your AI coding agents (MCP)`
- `Show HN: Give your AI coding agents shared state – one SQLite file, MCP server`

## URL

`https://github.com/<you>/agent-bridge`

## First comment (the one that actually matters on HN)

I run more than one AI coding agent at once — a planner in a chat window, a
couple of terminal agents (Claude Code, Codex) in different repos, and some
scheduled jobs. The agents are individually great and collectively amnesiac:
every session starts cold, work gets redone, and "handoffs" are me copy-pasting
context between windows all day.

agent-bridge is the shared state I built to fix that, extracted and rebuilt
clean from a larger personal system. It's a single MCP server backed by one
SQLite file. Any MCP-speaking agent can call it. It holds five things and
deliberately nothing else:

- owned context sections (single-writer ownership)
- a rolling cross-agent activity log
- a handoff queue (one agent dispatches work, another picks it up, whoever
  finishes clears it)
- per-agent state snapshots
- one FTS5 full-text search across all of it

No server to host, no vector DB, no cloud. `uv sync && uv run pytest` and you've
got 52 green tests; register it with `claude mcp add` and your agents share a
brain.

Two design decisions I'd call out:

1. The core logic is transport-free — every tool is a plain async function over
   a SQLite connection, and the MCP server is a thin wrapper. That's why the test
   suite needs no live MCP client, and the diagnostics CLI reuses the exact same
   code.
2. There's exactly one invariant doing most of the work: every write updates the
   FTS search index in the same transaction. No background reindexer to fall
   behind. `health` checks it; `rebuild_index` repairs it.

The biggest lesson building it was a subtraction. I tried to grow this into a
semantic knowledge store with embeddings, measured what agents actually searched
for, found that almost every "miss" was for content that was never in the bridge
to begin with, and deleted the vector roadmap. It coordinates; it doesn't try to
remember everything. There's a longer writeup of the whole one-person "AI
operating system" it came from in the repo's docs/ if that's interesting.

Happy to answer anything about the design.

## Anticipated questions (prep, don't paste)

- *Why not just use files / a git repo?* Files have no ownership model, no
  atomic FTS index, and no query surface; you end up rebuilding this badly.
- *Why SQLite and not Postgres/Redis?* One person, one machine, zero ops. SQLite
  with WAL handles concurrent agents fine and the whole thing is a single file
  you can back up by copying.
- *Is this multi-machine?* No, by design. Single machine, single file. Sync
  across machines is a different problem; don't bolt it on here.
- *Security of letting agents write?* The bus is data only — no shell, no exec.
  Identity is an allowlist. The dangerous-actions guardrails are a separate layer
  (and intentionally not part of this release).
