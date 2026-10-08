"""Call the local pg-mcp server over stdio for homework demonstrations."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROJECT_DIR = Path(__file__).resolve().parents[1]


def _print_payload(payload: Any) -> None:
    """Print an MCP response as readable, UTF-8-friendly JSON or text."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            print(payload)
            return
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


async def run_query(question: str, database: str | None, return_type: str) -> None:
    """Start pg-mcp as a child process and call its query tool once."""
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "pg_mcp"],
        cwd=PROJECT_DIR,
    )

    async with (
        stdio_client(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        result = await session.call_tool(
            "query",
            arguments={
                "question": question,
                "database": database,
                "return_type": return_type,
            },
        )

        if result.structuredContent is not None:
            _print_payload(result.structuredContent)
            return

        for item in result.content:
            text = getattr(item, "text", None)
            if text is not None:
                _print_payload(text)


def main() -> None:
    """Parse command-line arguments and execute one natural-language query."""
    parser = argparse.ArgumentParser(
        description="Run one natural-language database query through the local pg-mcp server."
    )
    parser.add_argument("question", nargs="+", help="Question; wrap it in double quotes")
    parser.add_argument("--database", default=None, help="Optional database name")
    parser.add_argument(
        "--sql-only",
        action="store_true",
        help="Generate SQL without executing it",
    )
    args = parser.parse_args()

    try:
        anyio.run(
            run_query,
            " ".join(args.question),
            args.database,
            "sql" if args.sql_only else "result",
        )
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Query failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
