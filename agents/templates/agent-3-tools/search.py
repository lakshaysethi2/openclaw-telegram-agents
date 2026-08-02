#!/usr/bin/env python3
"""Friend Bot docdocgo tool — GET /api/search ONLY.

Plain-text quote units. One SOURCE_PATH per unit. Never merge units.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# Replace with your docdocgo search API endpoint
API = "https://<your-search-api>/api/search"
UA = "FriendBot-docdocgo/2.3 (+search-only; plain-text-quotes)"
VALID_FILTERS = {"all", "books", "all-hawkins-books", "lectures"}
FILTER_HINTS = {
    "hawkins": "all-hawkins-books",
    "lecture": "lectures",
    "book": "books",
    "hawkins-books": "all-hawkins-books",
    "all_hawkins_books": "all-hawkins-books",
}

# Keep banner tiny — full rules live in DOCDOCGO.md (always in context).
HEADER = (
    "PLAIN TEXT search results (not images). "
    "Each UNIT = one SOURCE_PATH. Quote VERBATIM only; label paraphrase."
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Search docdocgo (GET /api/search only) — plain-text quote units",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./search.py "nothing is causing anything" 10
  ./search.py "surrender" 10 all-hawkins-books
  ./search.py "forgiveness" 10 lectures -c 500
  ./search.py "ego" 10 --partial
  ./search.py "love" 10 -w 260
""",
    )
    p.add_argument("query")
    p.add_argument(
        "limit",
        nargs="?",
        type=int,
        default=10,
        help="Results to show (min 10, default 10, max 25). Tool floors to 10.",
    )
    p.add_argument("filter", nargs="?", default="all")
    p.add_argument("-p", "--page", type=int, default=1)
    p.add_argument(
        "-c",
        "--context",
        type=int,
        default=350,
        help="API snippet padding around match (default 350, min 250).",
    )
    p.add_argument(
        "-g",
        "--group-distance",
        type=int,
        default=None,
        help="Optional groupDistance (server default 250).",
    )
    p.add_argument(
        "-w",
        "--window",
        type=int,
        default=260,
        help="Max display chars around match for VERBATIM (default 260).",
    )
    p.add_argument("--full", action="store_true", help="Show full API snippet (still one unit/path)")
    p.add_argument("--partial", action="store_true", help="wholeWords=false")
    p.add_argument("--case-sensitive", action="store_true")
    p.add_argument("--regex", action="store_true")
    p.add_argument("--json", action="store_true")
    return p


def find_match_span(snippet: str, query: str) -> tuple[int, int] | None:
    if not snippet or not query:
        return None
    q = query.strip()
    m = re.search(re.escape(q), snippet, flags=re.IGNORECASE)
    if m:
        return m.span()
    words = [w for w in q.split() if w]
    if len(words) >= 2:
        pat = r"\s+".join(re.escape(w) for w in words)
        m = re.search(pat, snippet, flags=re.IGNORECASE)
        if m:
            return m.span()
    for w in words:
        m = re.search(rf"\b{re.escape(w)}\b", snippet, flags=re.IGNORECASE)
        if m:
            return m.span()
    return None


def highlight(snippet: str, span: tuple[int, int] | None) -> str:
    """Mark match with [[...]] — never >>>/<<< (models misread those as media)."""
    if not span:
        return snippet
    a, b = span
    return f"{snippet[:a]}[[{snippet[a:b]}]]{snippet[b:]}"


def strip_api_markers(text: str) -> str:
    # API sometimes embeds >>>match<<<; normalize to [[match]].
    return re.sub(r">>>(.*?)<<<", r"[[\1]]", text, flags=re.DOTALL)


def trim_window(snippet: str, span: tuple[int, int] | None, window: int, full: bool) -> str:
    s = snippet.strip()
    if full or not s:
        return s
    if window <= 0:
        window = 260
    if not span:
        return (s[:window] + ("…" if len(s) > window else "")).strip()
    a, b = span
    mid = (a + b) // 2
    half = max(window // 2, (b - a) + 40)
    left = max(0, mid - half)
    right = min(len(s), mid + half)
    if left > 0:
        sp = s.find(" ", left)
        if 0 < sp < left + 40:
            left = sp + 1
    if right < len(s):
        sp = s.rfind(" ", max(left, right - 40), right)
        if sp > left:
            right = sp
    out = s[left:right].strip()
    if left > 0:
        out = "…" + out
    if right < len(s):
        out = out + "…"
    return out


def display_title(path: str) -> str:
    display = (
        str(path)
        .replace("_enxautogen_html", "")
        .replace("_html", "")
        .replace("_", " ")
        .strip()
    )
    return " ".join(w.capitalize() for w in display.split())


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    query = (args.query or "").strip()
    if not query:
        print('Usage: ./search.py "query" [limit] [filter]', file=sys.stderr)
        return 2
    if len(query) < 4 and not args.regex:
        print(
            "NOTE: query under 4 chars — enabling --partial (API min length).",
            file=sys.stderr,
        )
        args.partial = True

    filt = (args.filter or "all").strip()
    if filt in FILTER_HINTS:
        hint = FILTER_HINTS[filt]
        print(f"NOTE: filter '{filt}' → '{hint}'")
        filt = hint
    elif filt not in VALID_FILTERS:
        print(
            f"NOTE: filter '{filt}' not a preset "
            f"({', '.join(sorted(VALID_FILTERS))}). "
            "Typos may empty-result."
        )

    # Honor the requested limit exactly (clamp only for safety).
    requested = int(args.limit if args.limit is not None else 10)
    limit = max(10, min(requested, 25))
    page = max(1, int(args.page or 1))
    context = max(250, int(args.context if args.context and args.context > 0 else 350))
    window = int(args.window if args.window and args.window > 0 else 260)

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

    print(HEADER)
    print(f'SEARCH: "{query}"')
    extras = []
    if args.partial:
        extras.append("partial")
    if args.case_sensitive:
        extras.append("case")
    if args.regex:
        extras.append("regex")
    if args.full:
        extras.append("full-snippet")
    extra_s = f" extras={','.join(extras)}" if extras else ""
    print(
        f"opts: limit={limit} filter={filt} page={page} "
        f"context={context} window={window}{extra_s}"
    )
    print()

    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"ERROR HTTP {e.code}: {e.read().decode(errors='replace')[:300]}", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"ERROR {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2)[:12000])
        return 0

    if data.get("warning"):
        w = data["warning"]
        print(f"API warning: {w.get('message')}")
        if w.get("hint"):
            print(f"  {w['hint']}")
        print()

    results = data.get("results") or []
    total_matches = int(data.get("total_matches") or 0)
    total_files = int(data.get("files_count") or 0)
    total_pages = int(data.get("total_pages") or 0)
    page_n = int(data.get("page") or page)

    print(f"hits: {total_matches:,} matches in {total_files} files | page {page_n}/{max(total_pages, 1)}")
    print()

    if not results:
        print("No results. Try: simpler phrase | --partial | filter all | synonym")
        print()
        return 0

    for i, row in enumerate(results[:limit], 1):
        path = str(row.get("path") or "unknown")
        title = display_title(path)
        snippet = strip_api_markers((row.get("snippet") or "").strip())
        if snippet.startswith("..."):
            snippet = snippet[3:]
        if snippet.endswith("..."):
            snippet = snippet[:-3]
        snippet = re.sub(r"\s+", " ", snippet).strip()

        span = find_match_span(snippet, query)
        trimmed = trim_window(snippet, span, window, args.full)
        span2 = find_match_span(trimmed, query) if span else None
        shown = highlight(trimmed, span2) if span2 else trimmed
        shown = strip_api_markers(shown)

        mtext = ", ".join(f'"{w}"' for w in (row.get("match_text") or []))
        score = row.get("score")
        prox = row.get("proximity")
        chapter = row.get("chapter") or ""

        print(f"--- UNIT {i} ---")
        print(f"SOURCE_PATH: {path}")
        print(f"DISPLAY: {title}")
        if chapter:
            print(f"CHAPTER: {chapter}")
        print(f"META: score={score} proximity={prox} keywords={mtext}")
        print("VERBATIM:")
        print(shown if shown else "(empty snippet)")
        print(f"CITE: — {title}")
        print(f"path: `{path}`")
        print(f"--- END UNIT {i} ---")
        print()

    print("RULES: one blockquote per unit; cite path; no stitch; paraphrase: if restating")
    if total_pages > page_n:
        print(f"NEXT: ./search.py {query!r} {limit} {filt} -p {page_n + 1}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
