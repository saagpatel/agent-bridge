"""CLI entrypoint.

agent-bridge                  start the MCP server (stdio)
agent-bridge --status         print a compact status summary as JSON
agent-bridge --doctor         environment + DB diagnostics
agent-bridge --rebuild-index  repair FTS index drift
agent-bridge --export         regenerate the markdown mirror
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from . import __version__, config
from .db import open_db, repopulate_content_index
from .tools import export
from .tools import health as health_tools


async def _status() -> int:
    db = await open_db(config.db_path())
    try:
        print(json.dumps(await health_tools.status(db), indent=2))
    finally:
        await db.close()
    return 0


async def _doctor() -> int:
    path = config.db_path()
    print(f"agent-bridge v{__version__}")
    print(f"python: {sys.version.split()[0]}")
    print(f"db path: {path}")
    print(f"db exists: {path.exists()}")
    print(f"agents: {', '.join(config.agents())}")
    db = await open_db(path)
    try:
        report = await health_tools.health(db)
        print(f"schema version: {report['schema_version']}")
        print(f"rows: {report['counts']}")
        print(f"fts ok: {report['fts_index']['ok']}")
        ok = report["ok"]
    finally:
        await db.close()
    print(f"overall: {'OK' if ok else 'DEGRADED'}")
    return 0 if ok else 1


async def _rebuild_index() -> int:
    db = await open_db(config.db_path())
    try:
        counts = await repopulate_content_index(db)
        print(json.dumps({"rebuilt": counts, "ok": True}, indent=2))
    finally:
        await db.close()
    return 0


async def _export() -> int:
    db = await open_db(config.db_path())
    try:
        result = await export.export_markdown(db)
        print(json.dumps(result, indent=2))
    finally:
        await db.close()
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent-bridge", description=__doc__)
    parser.add_argument("--version", action="version", version=f"agent-bridge {__version__}")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true", help="print status JSON and exit")
    group.add_argument("--doctor", action="store_true", help="run diagnostics and exit")
    group.add_argument("--rebuild-index", action="store_true", help="repair FTS drift and exit")
    group.add_argument("--export", action="store_true", help="regenerate markdown mirror and exit")
    args = parser.parse_args()

    if args.status:
        sys.exit(asyncio.run(_status()))
    if args.doctor:
        sys.exit(asyncio.run(_doctor()))
    if args.rebuild_index:
        sys.exit(asyncio.run(_rebuild_index()))
    if args.export:
        sys.exit(asyncio.run(_export()))

    # Default: run the MCP server. Imported lazily so diagnostics don't require
    # the mcp SDK to be importable.
    from .server import run

    run()


if __name__ == "__main__":
    main()
