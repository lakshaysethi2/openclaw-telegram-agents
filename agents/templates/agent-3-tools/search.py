#!/usr/bin/env python3
"""docdocgo search + optional match-centered expand for Friend Bot.

Uses GET /api/search. With --expand, also uses GET /api/read/:path ONLY to
re-window around the true phrase / densest term cluster (fixes bad API
snippets when -c is large or multi-word proximity is sparse).
"""
from __future__ import annotations

import argparse
import json
import sys

from docdocgo_lib import (
    clean_display_path,
    expand_passage,
    highlight_match,
    http_get_json,
    query_terms,
)

VALID_FILTERS = {
    "all",
    "books",
    "all-hawkins-books",
    "lectures",
}
FILTER_HINTS = {
    "hawkins": "all-hawkins-books",
    "lecture": "lectures",
    "book": "books",
    "hawkins-books": "all-hawkins-books",
    "all_hawkins_books": "all-hawkins-books",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search docdocgo library (match-centered tooling)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./search.py "nothing is causing anything" 5
  ./search.py "nothing is causing anything" 3 --expand
  ./search.py "surrender" 5 all-hawkins-books
  ./search.py "forgiveness" 3 lectures --expand -c 300
  ./search.py "ego" 5 --partial
  ./read.py PATH -o OFFSET          # windowed read
  ./rag.py "query" 3                # semantic chunks
""",
    )
    p.add_argument("query", help="Search text (prefer a real phrase, ≥4 chars)")
    p.add_argument("limit", nargs="?", type=int, default=5, help="Results to show (default 5)")
    p.add_argument(
        "filter",
        nargs="?",
        default="all",
        help="all | books | all-hawkins-books | lectures | source path name",
    )
    p.add_argument("-p", "--page", type=int, default=1, help="Page number (default 1)")
    p.add_argument(
        "-c",
        "--context",
        type=int,
        default=300,
        help=(
            "API context chars (default 300). WARNING: large values (e.g. 1200) "
            "make multi-word grouping span distant hits and look like file-start junk. "
            "Prefer --expand for long passages."
        ),
    )
    p.add_argument(
        "--expand",
        action="store_true",
        help="Re-center each hit via /api/read around exact phrase or densest terms",
    )
    p.add_argument("--before", type=int, default=500, help="With --expand: chars before match")
    p.add_argument("--after", type=int, default=1000, help="With --expand: chars after match")
    p.add_argument(
        "--max-chars",
        type=int,
        default=3500,
        help="With --expand: max passage size (default 3500)",
    )
    p.add_argument("--full", action="store_true", help="Do not locally truncate API snippets")
    p.add_argument("--partial", action="store_true", help="wholeWords=false")
    p.add_argument("--case-sensitive", action="store_true")
    p.add_argument("--regex", action="store_true")
    p.add_argument("--json", action="store_true", help="Raw JSON (search only)")
    p.add_argument("--no-clean", action="store_true", help="Keep WEBVTT timestamps in expand")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = (args.query or "").strip()
    if not query:
        print('Usage: ./search.py "query" [limit] [filter] [options]', file=sys.stderr)
        return 2
    if len(query) < 4 and not args.regex:
        print(
            "⚠️  Query under 4 chars — prefer fuller phrases.",
            file=sys.stderr,
        )

    filt = (args.filter or "all").strip()
    if filt in FILTER_HINTS:
        hint = FILTER_HINTS[filt]
        print(f"⚠️  Filter '{filt}' → using '{hint}' instead.")
        filt = hint
    elif filt not in VALID_FILTERS and filt != "all":
        print(
            f"ℹ️  Filter '{filt}' is not a known preset "
            f"({', '.join(sorted(VALID_FILTERS))}). Typos silent-empty."
        )

    limit = max(1, min(int(args.limit or 5), 25))
    page = max(1, int(args.page or 1))
    context = int(args.context if args.context and args.context > 0 else 300)
    if context > 500 and not args.expand:
        print(
            f"⚠️  context={context} can produce sparse multi-word groups that look "
            "like lecture intros. Prefer default 300 + --expand for long quotes."
        )

    params: dict = {
        "q": query,
        "limit": limit,
        "page": page,
        "filter": filt,
        "context": context,
    }
    if args.partial:
        params["wholeWords"] = "false"
    if args.case_sensitive:
        params["caseSensitive"] = "true"
    if args.regex:
        params["useRegex"] = "true"

    print()
    print(f'🔍  docdocgo › "{query}"')
    extras = []
    if args.partial:
        extras.append("partial")
    if args.expand:
        extras.append("EXPAND")
    if args.case_sensitive:
        extras.append("case")
    if args.regex:
        extras.append("regex")
    extra_s = f" | {', '.join(extras)}" if extras else ""
    print(
        f"    Limit: {limit} | Filter: {filt} | Page: {page} | Context: {context}{extra_s}"
    )
    print("    tools: search.py | read.py | rag.py")
    print()

    try:
        data = http_get_json("/api/search", params)
    except Exception as e:  # noqa: BLE001
        print(f"❌  Request failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2)[:12000])
        return 0

    results = data.get("results") or []
    total_matches = int(data.get("total_matches") or 0)
    total_files = int(data.get("files_count") or 0)
    api_total_pages = data.get("total_pages")
    real_pages = max(1, (total_matches + limit - 1) // limit) if total_matches else 0
    page_n = int(data.get("page") or page)

    plural = "match" if total_matches == 1 else "matches"
    file_plural = "file" if total_files == 1 else "files"
    print(f"📚  {total_matches:,} {plural} across {total_files} {file_plural}")
    if total_matches:
        print(
            f"📄  Page {page_n} · showing up to {limit} · ~{real_pages} page(s) "
            f"(ignore API total_pages={api_total_pages!r})"
        )
    print()

    if not results:
        print("   No results found.")
        print()
        print("   Try: simpler synonym · --partial · filter all · ./rag.py \"...\"")
        print()
        return 0

    terms = query_terms(query)
    sparse_warned = False

    for i, row in enumerate(results[:limit], 1):
        path = row.get("path", "unknown")
        match_count = row.get("match_count", 0)
        score = row.get("score", 0)
        snippet = (row.get("snippet") or "").strip()
        chapter = row.get("chapter") or ""
        match_text = row.get("match_text") or []
        proximity = row.get("proximity", "")
        offset = row.get("offset", "")
        display = clean_display_path(str(path))

        print(f"╭──  #{i}  ───────────────────────────────")
        print(f"│ 📄 {display}")
        print(f"│ 🔗 path: {path}")
        if chapter:
            print(f"│ 📖 {chapter}")
        mtext = ", ".join(f'"{w}"' for w in match_text)
        try:
            prox_n = int(proximity) if proximity != "" else 0
        except (TypeError, ValueError):
            prox_n = 0
        sparse = prox_n > max(800, context * 2)
        prox_note = f" | proximity {proximity}"
        if sparse:
            prox_note += " ⚠️ SPARSE (words far apart — use --expand)"
            sparse_warned = True
        print(f"│ 🎯 {match_count} matches | score {score}{prox_note}")
        print(f"│ 📍 offset: {offset} | keywords: {mtext}")
        print(f"│ 📎 expand: ./read.py {path} -o {offset} -q {query!r}")

        if args.expand:
            try:
                exp = expand_passage(
                    str(path),
                    query,
                    offset_hint=int(offset) if offset != "" else None,
                    before=args.before,
                    after=args.after,
                    max_chars=args.max_chars,
                    clean=not args.no_clean,
                )
                print(f"│ ✅ centered via {exp['method']} @ {exp['match_start']}-{exp['match_end']}")
                print("│")
                # wrap long lines lightly
                body = exp["passage"]
                print(f"│ {body}")
            except Exception as e:  # noqa: BLE001
                print(f"│ ❌ expand failed: {e}")
                if snippet:
                    print(f"│ fallback snippet: {snippet[:500]}")
        else:
            if snippet:
                clean = snippet
                if clean.startswith("..."):
                    clean = clean[3:]
                if clean.endswith("..."):
                    clean = clean[:-3]
                clean = clean.strip()
                # Prefer local re-center highlight inside API snippet
                shown = highlight_match(clean, query, terms)
                if not args.full and len(shown) > 420:
                    # keep highlight region if present
                    hi = shown.find(">>>")
                    if hi >= 0:
                        left = max(0, hi - 120)
                        shown = ("..." if left else "") + shown[left : left + 420] + "..."
                    else:
                        shown = shown[:420] + "..."
                print("│")
                print(f"│ {shown}")
                if sparse:
                    print("│")
                    print("│ 💡 Re-run with --expand to pull the real paragraph around the phrase.")
        print("╰───────────────────────────────────────")
        print()

    if sparse_warned and not args.expand:
        print("⚠️  One or more hits were sparse multi-word groups.")
        print(f'   Fix: ./search.py {query!r} {limit} {filt} --expand')
        print()
    if real_pages > page_n:
        print(f"➡️  More: ./search.py {query!r} {limit} {filt} -p {page_n + 1}")
        print()
    if not args.expand:
        print(f'💬  Deep passage: ./search.py {query!r} {limit} {filt} --expand')
        print(f'🧠  Semantic:     ./rag.py {query!r} 3')
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
