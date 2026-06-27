# Build-in-public thread (X / LinkedIn)

> Staged — do not post without operator review. Replace <repo-url> and confirm
> the cost figures you're comfortable sharing publicly (see SANITIZATION-REPORT).

## X / Twitter thread

**1/**
I run a fleet of AI coding agents as one person — a planner model, two terminal
agents in different repos, background jobs.

The hard part was never the agents. It was that none of them knew what the others
did.

So I built them a shared brain. Open-sourcing it today 🧵

**2/**
The problem, concretely:

Every agent session starts cold. The planner designs what an executor already
built. One agent "finishes" what another quietly broke. Handoffs = me
copy-pasting context between windows all day.

Individually brilliant. Collectively amnesiac.

**3/**
agent-bridge is the fix: one SQLite file behind an MCP server that any agent can
read and write.

It holds 5 things and nothing else:
• owned context notes
• a cross-agent activity feed
• a handoff queue
• state snapshots
• full-text search over all of it

**4/**
The handoff queue is the piece that turns "several agents" into "a team":

one agent dispatches a unit of work → another picks it up → whoever finishes
clears it.

Same primitive a kanban board gives humans. Agents needed their own.

**5/**
Best decision: one invariant carries the whole design.

Every write updates the search index in the SAME transaction. No background
reindexer that can drift. A health check verifies it; one command rebuilds it.

Find the one invariant, enforce it everywhere.

**6/**
Best feature I shipped was the one I deleted.

I tried to grow this into a semantic memory store with embeddings. Then I
measured what agents actually searched for — almost every miss was for content
that was never in the bridge.

Killed the vector roadmap. It coordinates; it doesn't hoard.

**7/**
What it costs to run a fleet like this:

measured at API rates, my agent usage runs ~$1–3.5k/month of compute — but it
runs under a flat subscription, so out-of-pocket is a fixed line item.

That gap is the whole reason one person can run a team of agents.

**8/**
It's MIT, Python, zero infra. `uv sync && uv run pytest` → 52 green tests.
Register with one `claude mcp add` line and your agents share state.

Repo + a full writeup of the one-person "AI operating system" it came from:
<repo-url>

If you run >1 agent, you have this problem. Here's the fix.

## LinkedIn variant (single post)

I spent the last year building something unusual: an "operating system" for a
fleet of AI coding agents, run by one person.

The agents were never the hard part. The hard part was continuity — none of them
knew what the others had done, so every session started cold and half the work
was me shuttling context between windows by hand.

The core fix is a shared state bus: a single SQLite file behind an MCP server
that every agent reads and writes. Owned context notes, a cross-agent activity
feed, a handoff queue, snapshots, and full-text search — and deliberately nothing
more. I tried to make it a semantic memory store and walked it back when the data
said coordination, not recall, was the real need.

I've open-sourced that piece (MIT), plus a primary-source writeup of how the
whole system works and what it costs to run. Link in comments.
