#!/usr/bin/env python3
"""Shared helpers for Friend Bot docdocgo tools."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE = "https://docdocgo.lak.nz"
UA = "FriendBot-docdocgo/2.0 (+openclaw-agent-3)"


def http_get_json(path: str, params: dict[str, Any] | None = None, timeout: int = 45) -> dict:
    url = f"{BASE}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def http_post_json(path: str, payload: dict[str, Any], timeout: int = 60) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        method="POST",
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def clean_display_path(path: str) -> str:
    display = (
        str(path)
        .replace("_enxautogen_html", "")
        .replace("_html", "")
        .replace("_", " ")
        .strip()
    )
    return " ".join(w.capitalize() for w in display.split())


_STOP = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "been", "being", "it", "that", "this", "with", "as",
    "by", "at", "from", "not", "no", "do", "does", "did", "we", "you", "i",
}


def query_terms(query: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9']+", query.lower())
    meaningful = [w for w in words if w not in _STOP and len(w) > 1]
    return meaningful or words


def strip_webvtt(text: str) -> str:
    """Drop WEBVTT chrome / timestamp lines for cleaner quotes."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            out.append("")
            continue
        if s.upper() == "WEBVTT":
            continue
        if re.fullmatch(r"\d+", s):
            continue
        if re.match(r"\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}", s):
            continue
        if s.startswith("====_") and s.endswith("_===="):
            continue
        out.append(line)
    cleaned = "\n".join(out)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def find_phrase_span(content: str, query: str) -> tuple[int, int] | None:
    if not query.strip():
        return None
    m = re.search(re.escape(query.strip()), content, flags=re.IGNORECASE)
    if m:
        return m.start(), m.end()
    # collapse whitespace variant
    pat = r"\s+".join(re.escape(w) for w in query.split())
    m = re.search(pat, content, flags=re.IGNORECASE)
    if m:
        return m.start(), m.end()
    return None


def find_best_term_span(content: str, terms: list[str]) -> tuple[int, int] | None:
    """Smallest window covering the densest occurrence of query terms."""
    if not content or not terms:
        return None
    lower = content.lower()
    positions: list[tuple[int, int, str]] = []  # start, end, term
    for t in terms:
        if len(t) < 2:
            continue
        for m in re.finditer(rf"\b{re.escape(t)}\b", lower):
            positions.append((m.start(), m.end(), t))
    if not positions:
        # fallback substring
        for t in terms:
            idx = lower.find(t)
            if idx >= 0:
                positions.append((idx, idx + len(t), t))
    if not positions:
        return None
    positions.sort(key=lambda x: x[0])

    best = None  # (score, span_len, start, end)
    n = len(positions)
    for i in range(n):
        seen: set[str] = set()
        end = positions[i][1]
        for j in range(i, n):
            seen.add(positions[j][2])
            end = max(end, positions[j][1])
            start = positions[i][0]
            span = end - start
            # prefer more unique terms, then tighter span
            score = len(seen) * 1_000_000 - span
            cand = (score, span, start, end)
            if best is None or cand > best:
                best = cand
            # no point expanding forever once all terms seen and span huge
            if len(seen) == len(set(terms)) and span > 8000:
                break
    if best is None:
        return None
    return best[2], best[3]


def window_around(
    content: str,
    start: int,
    end: int,
    before: int = 500,
    after: int = 900,
    max_chars: int = 4000,
) -> tuple[str, int, int]:
    before = max(0, before)
    after = max(0, after)
    left = max(0, start - before)
    right = min(len(content), end + after)
    # enforce max_chars centered on match
    if right - left > max_chars:
        mid = (start + end) // 2
        half = max_chars // 2
        left = max(0, mid - half)
        right = min(len(content), left + max_chars)
        left = max(0, right - max_chars)
    chunk = content[left:right]
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(content) else ""
    return f"{prefix}{chunk}{suffix}", left, right


def highlight_match(text: str, query: str, terms: list[str] | None = None) -> str:
    """Wrap best match with >>> <<< for the agent to spot center."""
    span = find_phrase_span(text, query)
    if not span and terms:
        # highlight densest term cluster inside the already-windowed text
        local = find_best_term_span(text, terms)
        if local:
            span = local
    if not span:
        return text
    a, b = span
    return f"{text[:a]}>>>{text[a:b]}<<<{text[b:]}"


def expand_passage(
    path: str,
    query: str,
    offset_hint: int | None = None,
    before: int = 500,
    after: int = 900,
    max_chars: int = 3500,
    clean: bool = True,
) -> dict[str, Any]:
    """Read full doc and return a passage centered on the best match for query."""
    data = http_get_json(f"/api/read/{urllib.parse.quote(path, safe='')}")
    content = data.get("content") or ""
    if not content:
        raise RuntimeError(f"empty content for {path}")

    terms = query_terms(query)
    span = find_phrase_span(content, query)
    method = "exact_phrase"
    if not span:
        span = find_best_term_span(content, terms)
        method = "dense_terms"
    if not span:
        # fall back to API offset hint
        if offset_hint is not None and 0 <= offset_hint < len(content):
            span = (offset_hint, min(len(content), offset_hint + max(10, len(query))))
            method = "offset_hint"
        else:
            span = (0, min(len(content), max_chars))
            method = "file_start_fallback"

    start, end = span
    passage, left, right = window_around(
        content, start, end, before=before, after=after, max_chars=max_chars
    )
    if clean:
        passage = strip_webvtt(passage)
        # re-collapse whitespace for display
        passage = re.sub(r"\s+", " ", passage).strip()
    highlighted = highlight_match(passage, query, terms)
    return {
        "path": path,
        "method": method,
        "match_start": start,
        "match_end": end,
        "window_start": left,
        "window_end": right,
        "file_chars": len(content),
        "passage": highlighted,
        "raw_passage": passage,
    }
