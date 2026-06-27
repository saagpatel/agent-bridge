# Awesome-list submission

> Staged. Submit as a PR to the relevant lists after the repo is public. Confirm
> each list's exact format/category from its CONTRIBUTING before opening the PR.

## Target lists (in priority order)

1. **awesome-mcp-servers** (e.g. `punkpeye/awesome-mcp-servers`,
   `wong2/awesome-mcp-servers`) — the highest-intent audience.
2. **awesome-claude / awesome-claude-code** type lists — agent-tooling readers.
3. Any "awesome-ai-agents" / "awesome-agent-infrastructure" list with a
   coordination/memory category.

## Entry (one-liner format most lists use)

```markdown
- [agent-bridge](https://github.com/<you>/agent-bridge) - Shared-state bus for multiple AI coding agents: owned context, activity feed, handoff queue, snapshots, and FTS5 recall in one SQLite-backed MCP server.
```

## Entry (table format, if the list uses one)

```markdown
| [agent-bridge](https://github.com/<you>/agent-bridge) | Python | A SQLite-backed MCP server giving AI agents a shared memory bus — context sections, activity log, handoff queue, snapshots, full-text recall. |
```

## Category placement

Most fitting under a **"Coordination / Memory / State"** or **"Productivity"**
section. If the list splits by official vs community, it's community. If it splits
by transport, it's **stdio**.

## PR description boilerplate

> Adds agent-bridge, an MCP server that gives multiple AI coding agents shared
> coordination state (context sections, a cross-agent activity feed, a handoff
> dispatch queue, snapshots, and FTS5 search) backed by a single SQLite file.
> MIT-licensed, Python 3.12+, transport-free core with a full test suite. Fills
> the "how do my agents share state" gap rather than adding another data-source
> connector.
