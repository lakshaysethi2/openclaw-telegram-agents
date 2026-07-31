#!/usr/bin/env python3
"""Friend Bot docdocgo tool — GET /api/search ONLY.

No /api/read, /api/rag, or /api/files.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://docdocgo.lak.nz/api/search"
UA = "FriendBot-docdocgo/2.1 (+search-only)"
VALID_FILTERS = {"all", "books", "all-hawkins-books", "lectures"}
FILTER_HINTS = {
    "hawkins": "all-hawkins-books",
    "lecture": "lectures",
    "book": "books",
    "hawkins-books": "all-hawkins-books",
    "all_hawkins_books": "all-hawkins-books",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search docdocgo (GET /api/search only)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./search.py "nothing is causing anything" 5
  ./search.py "surrender" 5 all-hawkins-books
  ./search.py "forgiveness" 3 lectures -c 500
  ./search.py "ego" 5 --partial
  ./search.py "love" 5 -p 2
""",
    )
    p.add_argument("query")
    p.add_argument("limit", nargs="?", type=int, default=5)
    p.add_argument("filter", nargs="?", default="all")
    p.add_argument("-p", "--page", type=int, default=1)
    p.add_argument(
        "-c",
        "--context",
        type=int,
        default=400,
        help="Snippet padding around match (default 400). Safe to raise; grouping is separate server-side.",
    )
    p.add_argument(
        "-g",
        "--group-distance",
        type=int,
        default=None,
        help="Optional groupDistance (server default 250). Rarely needed.",
    )
    p.add_argument("--full", action="store_true", help="Do not locally truncate display")
    p.add_argument("--partial", action="store_true", help="wholeWords=false")
    p.add_argument("--case-sensitive", action="store_true")
    p.add_argument("--regex", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def highlight(snippet: str, query: str) -> str:
    if not snippet or not query:
        return snippet
    m = re.search(re.escape(query.strip()), snippet, flags=re.IGNORECASE)
    if not m:
        # loose whitespace
        pat = r"\s+".join(re.escape(w) for w in query.split())
        m = re.search(pat, snippet, flags=re.IGNORECASE)
    if not m:
        return snippet
    a, b = m.span()
    return f"{snippet[:a]}>>>{snippet[a:b]}<<<{snippet[b:]}"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = (args.query or "").strip()
    if not query:
        print('Usage: ./search.py "query" [limit] [filter]', file=sys.stderr)
        return 2
    if len(query) < 4 and not args.regex:
        print("⚠️  Query under 4 chars — API may return nothing.", file=sys.stderr)

    filt = (args.filter or "all").strip()
    if filt in FILTER_HINTS:
        hint = FILTER_HINTS[filt]
        print(f"⚠️  Filter '{filt}' → '{hint}'")
        filt = hint
    elif filt not in VALID_FILTERS:
        print(
            f"ℹ️  Filter '{filt}' not a preset ({', '.join(sorted(VALID_FILTERS))}). "
            "Typos may empty-result (API may include warning)."
        )

    limit = max(1, min(int(args.limit or 5), 25))
    page = max(1, int(args.page or 1))
    context = int(args.context if args.context and args.context > 0 else 400)

    params: dict = {
        "q": query,
        "limit": limit,
        "page": page,
        "filter": filt,
        "context": context,
    }
    if args.group_distance and args.group_distance > 0:
        params["groupDistance"] = int(args.group_distance)
    if args.partial:
        params["wholeWords"] = "false"
    if args.case_sensitive:
        params["caseSensitive"] = "true"
    if args.regex:
        params["useRegex"] = "true"

    print()
    print(f'🔍  docdocgo search › "{query}"')
    extras = []
    if args.partial:
        extras.append("partial")
    if args.case_sensitive:
        extras.append("case")
    if args.regex:
        extras.append("regex")
    extra_s = f" | {', '.join(extras)}" if extras else ""
    print(f"    Limit: {limit} | Filter: {filt} | Page: {page} | Context: {context}{extra_s}")
    print("    Endpoint: GET /api/search only")
    print()

    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"❌  HTTP {e.code}: {e.read().decode(errors='replace')[:300]}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"❌  {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2)[:12000])
        return 0

    if data.get("warning"):
        w = data["warning"]
        print(f"⚠️  API warning: {w.get('message')}")
        if w.get("hint"):
            print(f"    {w['hint']}")
        print()

    results = data.get("results") or []
    total_matches = int(data.get("total_matches") or 0)
    total_files = int(data.get("files_count") or 0)
    total_pages = int(data.get("total_pages") or 0)
    page_n = int(data.get("page") or page)
    opts = data.get("options") or {}

    print(f"📚  {total_matches:,} matches across {total_files} files")
    if total_matches:
        print(
            f"📄  Page {page_n}/{max(total_pages, 1)} · limit {limit} · "
            f"contextChars={opts.get('contextChars')} · groupDistance={opts.get('groupDistance')}"
        )
    print()

    if not results:
        print("   No results.")
        print("   Try: simpler phrase · --partial · filter all · different synonym")
        print()
        return 0

    for i, row in enumerate(results[:limit], 1):
        path = row.get("path", "unknown")
        display = (
            str(path)
            .replace("_enxautogen_html", "")
            .replace("_html", "")
            .replace("_", " ")
            .strip()
        )
        display = " ".join(w.capitalize() for w in display.split())
        snippet = (row.get("snippet") or "").strip()
        if snippet.startswith("..."):
            snippet = snippet[3:]
        if snippet.endswith("..."):
            snippet = snippet[:-3]
        snippet = snippet.strip()
        shown = highlight(snippet, query)
        if not args.full and len(shown) > 500:
            hi = shown.find(">>>")
            if hi >= 0:
                left = max(0, hi - 160)
                shown = ("..." if left else "") + shown[left : left + 500] + "..."
            else:
                shown = shown[:500] + "..."

        print(f"╭──  #{i}  ───────────────────────────────")
        print(f"│ 📄 {display}")
        print(f"│ 🔗 path: {path}")
        if row.get("chapter"):
            print(f"│ 📖 {row['chapter']}")
        mtext = ", ".join(f'"{w}"' for w in (row.get("match_text") or []))
        print(
            f"│ 🎯 score {row.get('score')} | matches {row.get('match_count')} | "
            f"proximity {row.get('proximity')} | offset {row.get('offset')}"
        )
        print(f"│ 🔑 {mtext}")
        if shown:
            print("│")
            print(f"│ {shown}")
        print("╰───────────────────────────────────────")
        print()

    if total_pages > page_n:
        print(f"➡️  Next page: ./search.py {query!r} {limit} {filt} -p {page_n + 1}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
