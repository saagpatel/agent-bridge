# How a one-person AI operating system actually works

*A primary-source account of running a fleet of AI coding agents as a single
coordinated system — the architecture, the real costs, and what a year of
building it taught me. `agent-bridge` (this repo) is the open-source distillation
of its coordination spine.*

---

## The premise

I am one person. At any given moment I might have a planning model in a chat
window, two terminal coding agents working different repositories, and a handful
of scheduled jobs running in the background. On paper that's a team. In practice,
for a long time, it was four strangers with amnesia.

The agents were individually excellent and collectively useless at *continuity*.
Each session started cold. The planner would design something the executor had
already half-built. One agent would "finish" a task another had quietly broken.
Handoffs happened the way they happen for everyone right now: I copy-pasted
context from one window into another, by hand, all day.

The thing I actually built over the last year is not a better agent. It's the
**operating system around the agents** — the shared state, the rules, the
memory, and the schedulers that turn a pile of capable models into something that
behaves like one system with one memory. This is how it works.

## The five layers

A one-person AI operating system, it turns out, has the same layers an operating
system has.

### 1. A shared state bus (the part I open-sourced)

The foundational problem is shared memory. Agents need a single place to answer:
*What is everyone working on? What was decided? What's been handed to whom? What
happened recently?*

My answer is a single SQLite file behind an MCP server. Any agent that speaks the
[Model Context Protocol](https://modelcontextprotocol.io) can read and write it.
It holds five things and deliberately nothing else:

- **Owned context sections** — long-lived shared notes with single-writer
  ownership, so the planner's roadmap can't be silently clobbered by an executor.
- **An activity log** — a rolling, cross-agent "what happened" feed.
- **Handoffs** — a dispatch queue. One agent assigns a unit of work; another
  picks it up; whoever finishes clears it. This is the primitive that makes a
  *team* out of a set of processes.
- **Snapshots** — periodic per-agent state captures for warm starts.
- **Full-text recall** — one search across all of the above.

This layer is what `agent-bridge` is. The biggest lesson from building it was a
*subtraction*: I spent real effort trying to grow it into a semantic knowledge
store with embeddings and vector search, and then I measured what people actually
searched for. The overwhelming majority of "missed" queries were for content
that was never in the bridge to begin with — they belonged in a notes vault, not
the coordination state. I deleted the vector roadmap. **The bus coordinates; it
does not remember everything.** Lexical FTS5 search was enough, and "enough,
forever" beats "impressive, fragile."

### 2. A permission layer that fails closed

Giving autonomous agents a real shell on your actual machine is the part people
correctly find terrifying. The discipline that makes it sane is ordinary
security engineering applied to a new actor:

- **Deny by default on the things that can't be undone or shouldn't be read** —
  credential directories, destructive operations against anything that isn't
  local, history rewrites, pushes to protected branches.
- **Defense in depth.** The agent's own instructions are advisory; the actual
  enforcement lives in deterministic hooks that run *outside* the model, so a
  confused or manipulated agent can't talk its way past them.
- **Mode-appropriate trust.** Routine work in a trusted repo runs with light
  friction; untrusted or adversarial code runs in an isolated, network-limited
  workspace where the operator owns every call.

I'm deliberately not publishing the exact rule contents — a defense you've
itemized for an attacker is a weaker defense. The *shape*, though, is the
reusable part: treat the agent as an untrusted-by-default actor, and put the
guardrails where the agent can't reach them.

### 3. Persistent memory

Coordination state is short-lived by design. Durable knowledge — who I am, hard
lessons learned, project facts not derivable from the code — lives in a separate,
file-based memory that's loaded at the start of every session and consolidated
between sessions. The rule that keeps it useful: **don't store what the code or
git history already shows.** Memory is for the non-obvious. A memory file that
restates the repo structure is just lag waiting to mislead you.

### 4. Schedulers and background jobs

A real operating system does things while you sleep. Mine runs scheduled jobs —
health sweeps across the project portfolio, cost snapshots, index maintenance,
nightly reconciliations. The interesting constraint here is that a headless,
scheduled agent run is a *different environment* from an interactive one: it
loads a much larger tool surface, it has no human to approve a prompt, and it has
to be pinned to a minimal, explicit set of capabilities or it will either stall
or do too much. Most of my scheduling bugs were really "I assumed the cron run
looked like my terminal" bugs.

### 5. The portfolio it operates on

All of this exists to ship things. The system manages a portfolio of dozens of
projects — desktop apps, iOS apps, CLIs, web tools — each with its own context
file, its own verification commands, and its own state tracked in the bus. The
operating system is the thing that lets one person keep that many balls in the
air without dropping continuity between them.

## What it costs

Honest numbers, because vague ones aren't useful.

The *consumption* is large. Measured at API-equivalent rates, my coding-agent
usage runs in the low-thousands of dollars per month — months in 2026 landed
between roughly **$1,000 and $3,500** of API-equivalent compute. The *out-of-pocket*
cost is far lower, because that volume runs under a flat subscription rather than
metered API billing. The gap between those two numbers is, frankly, the whole
economic story of why a one-person operation can run a fleet at all: the
subscription turns "thousands of dollars of compute" into a fixed line item, and
the operating system turns that compute into shipped work instead of wasted
re-explanation.

The other cost is real and unpriced: **the system itself is a product you
maintain.** Hooks break. Schedulers drift. A model upgrade changes behavior. If
you build this, budget for the fact that you've taken on a second job as the
sysadmin of your own agents.

## The five lessons that generalize

1. **Coordination beats capability at the margin.** A second agent adds far more
   value when it can see what the first one did than when it's merely smarter in
   isolation. The shared bus was the highest-leverage thing I built.
2. **Put enforcement outside the model.** Anything you rely on the agent to
   *choose* to do, it will eventually skip under pressure. Anything a deterministic
   hook enforces, it can't.
3. **Subtract aggressively.** The best feature I shipped to the coordination layer
   was the vector-search feature I deleted. Scope that says no is scope you can
   maintain.
4. **One invariant, enforced everywhere, beats many checks enforced sometimes.**
   In the bus, the rule "every write updates the search index in the same
   transaction" removed an entire category of bug. Find the one invariant.
5. **The scheduled environment is not the interactive one.** Test your automation
   in the environment it will actually run in, not the one you developed it in.

## What's reusable, and what isn't

The personal layers — my memory, my permission rules, my portfolio — are mine,
and some of them (the security internals especially) are deliberately private.
But the **coordination spine generalizes cleanly**, because coordination is the
same problem for everyone running more than one agent.

So that's the piece I extracted, rebuilt from scratch with nothing
machine-specific in it, and released: [`agent-bridge`](../README.md). It's the
shared memory bus — context sections, an activity feed, a handoff queue,
snapshots, and full-text recall — as a single SQLite-backed MCP server you can
point your own fleet at in about five minutes.

If you're running more than one coding agent today, you already have this problem.
You're just solving it by copy-paste. This is the part of my system you can have.
