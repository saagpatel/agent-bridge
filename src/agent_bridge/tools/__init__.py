"""Tool core functions. Each is a plain async function taking a db connection,
so it can be unit-tested without a live MCP transport. server.py binds them to
MCP tool endpoints."""
