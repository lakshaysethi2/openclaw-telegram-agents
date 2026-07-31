#!/usr/bin/env python3
"""Windowed docdocgo reader — never dumps whole books into chat context.

GET /api/read/:path is used only to slice a passage around offset / query.
"""
from __future__ import annotations

import argparse
import sys

from docdocgo_lib import clean_display_path, expand_passage, http_get_json, window_around


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Read a centered window from a docdocgo source path",
        epilog="""
Examples:
  ./read.py Integration_of_Spirituality_and_Personal_Life_Feb_2003_Part_1_enxautogen_html -q "nothing is causing anything"
  ./read.py Freedom_Morality_and_Ethics_Nov_2008_Part_3_enxautogen_html -o 45680
  ./read.py I_reality_and_subj -q "divine indifference" --before 300 --after 800
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("path", help="Exact source path from search results")
    p.add_argument("-o", "--offset", type=int, default=None, help="Byte/char offset hint from search")
    p.add_argument("-q", "--query", default="", help="Phrase to center on (preferred over bare offset)")
    p.add_argument("--before", type=int, default=500)
    p.add_argument("--after", type=int, default=1000)
    p.add_argument("--max-chars", type=int, default=3500)
    p.add_argument("--no-clean", action="store_true", help="Keep WEBVTT timestamps")
    p.add_argument(
        "--raw-offset-only",
        action="store_true",
        help="Ignore query densify; slice strictly around --offset",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = (args.path or "").strip()
    if not path:
        print("path required", file=sys.stderr)
        return 2

    try:
        if args.raw_offset_only:
            if args.offset is None:
                print("--raw-offset-only requires -o/--offset", file=sys.stderr)
                return 2
            data = http_get_json(f"/api/read/{path}")
            content = data.get("content") or ""
            start = max(0, min(len(content), args.offset))
            end = min(len(content), start + 40)
            passage, left, right = window_around(
                content, start, end, before=args.before, after=args.after, max_chars=args.max_chars
            )
            print()
            print(f"📖  {clean_display_path(path)}")
            print(f"🔗  path: {path}")
            print(f"📍  raw window {left}-{right} / {len(content)} chars")
            print()
            print(passage if args.no_clean else " ".join(passage.split()))
            print()
            return 0

        query = (args.query or "").strip()
        if not query and args.offset is None:
            print(
                "Provide -q \"phrase\" and/or -o OFFSET. Full-file dumps are blocked on purpose.",
                file=sys.stderr,
            )
            return 2
        if not query:
            # center on offset with a synthetic query
            query = " "

        exp = expand_passage(
            path,
            query if query.strip() else "the",
            offset_hint=args.offset,
            before=args.before,
            after=args.after,
            max_chars=args.max_chars,
            clean=not args.no_clean,
        )
        # If only offset given with blank-ish query, force offset method
        if not (args.query or "").strip() and args.offset is not None:
            data = http_get_json(f"/api/read/{path}")
            content = data.get("content") or ""
            start = max(0, min(len(content), args.offset))
            end = min(len(content), start + 40)
            passage, left, right = window_around(
                content, start, end, before=args.before, after=args.after, max_chars=args.max_chars
            )
            from docdocgo_lib import strip_webvtt
            import re
            body = passage if args.no_clean else re.sub(r"\s+", " ", strip_webvtt(passage)).strip()
            print()
            print(f"📖  {clean_display_path(path)}")
            print(f"🔗  path: {path}")
            print(f"📍  offset-window {left}-{right} / {len(content)} chars")
            print()
            print(body)
            print()
            return 0

        print()
        print(f"📖  {clean_display_path(path)}")
        print(f"🔗  path: {path}")
        print(
            f"📍  {exp['method']} match {exp['match_start']}-{exp['match_end']} "
            f"· window {exp['window_start']}-{exp['window_end']} / {exp['file_chars']} chars"
        )
        print()
        print(exp["passage"])
        print()
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"❌  {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
