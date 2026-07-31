#!/usr/bin/env python3
"""docdocgo semantic RAG chunks for deeper teaching answers."""
from __future__ import annotations

import argparse
import json
import sys

from docdocgo_lib import http_post_json


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Semantic RAG search (POST /api/rag)",
        epilog='Example: ./rag.py "nothing is causing anything" 3',
    )
    p.add_argument("query", help="Natural language query")
    p.add_argument("limit", nargs="?", type=int, default=3, help="Chunks (default 3, max 8)")
    p.add_argument("--source", action="append", default=[], help="Optional source filter (repeatable)")
    p.add_argument("--json", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = (args.query or "").strip()
    if not query:
        print('Usage: ./rag.py "query" [limit]', file=sys.stderr)
        return 2
    top_k = max(1, min(int(args.limit or 3), 8))
    payload = {"query": query, "top_k": top_k}
    if args.source:
        payload["sources"] = args.source

    print()
    print(f'🧠  docdocgo RAG › "{query}"')
    print(f"    top_k={top_k}")
    print()
    try:
        data = http_post_json("/api/rag", payload)
    except Exception as e:  # noqa: BLE001
        print(f"❌  {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2)[:12000])
        return 0

    results = data.get("results") or []
    if not results:
        print("   No chunks. Try ./search.py or different wording.")
        print()
        return 0

    for i, row in enumerate(results[:top_k], 1):
        chunk = row.get("chunk") or {}
        text = (chunk.get("text") or "").strip()
        source = chunk.get("source") or "?"
        score = row.get("score", "")
        tokens = chunk.get("token_count", "")
        print(f"╭──  RAG #{i}  ──────────────────────────────")
        print(f"│ 🔗 source: {source} | score {score} | ~{tokens} tokens")
        print("│")
        print(f"│ {text}")
        print("╰───────────────────────────────────────")
        print()
    print("Tip: pair with ./search.py \"...\" --expand for attributable path-level quotes.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
