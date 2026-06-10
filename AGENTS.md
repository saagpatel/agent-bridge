# AGENTS.md

## What This Project Is

`agent-bridge` is a Python 3.12 MCP server that provides a local SQLite-backed shared state bus for coding agents. It exposes owned context sections, activity logs, handoffs, snapshots, recall search, and health/status tools over stdio.

## Current State

The repo is on `feat/initial-release` with the v0.1.0 implementation present. It has a real test suite under `tests/`, package metadata in `pyproject.toml`, and architecture notes under `docs/`.

## Stack

- Python 3.12+
- MCP Python SDK
- SQLite / FTS5 via `aiosqlite`
- `uv`, `pytest`, and `ruff`

## How To Run

```sh
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run python -m agent_bridge --status
uv run python -m agent_bridge --doctor
```

Start the MCP server over stdio with:

```sh
uv run python -m agent_bridge
```

## Known Risks

- Treat bridge data as coordination state, not a credential store.
- Do not read or expose raw private transcripts, secrets, `.env` files, OAuth stores, browser profiles, or keychain material through this repo.
- Keep ownership and retention semantics explicit when adding write paths.

## Next Recommended Move

Before publishing or wiring this into more agents, run the full local test suite and verify the install/registration instructions against the target MCP client.
