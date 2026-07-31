# TOOLS.md — Friend Bot

## docdocgo (PRIMARY — search only)
```bash
./search.py "query" [limit] [filter]
./search.py "nothing is causing anything" 10
./search.py "surrender" 10 all-hawkins-books
./search.py "forgiveness" 10 lectures -c 500 -w 300
./search.py "ego" 10 --partial
```
- Endpoint: **only** `GET https://docdocgo.lak.nz/api/search`
- Output = plain-text **UNITs** (one `SOURCE_PATH` each) — **never images**
- Default **limit=10** (min 10 — never fewer; max 25)
- Guide: `DOCDOCGO.md` · https://github.com/friend-bot-dnd/docdocgo-api-guide
- Do **not** call `/api/read`, `/api/rag`, `/api/files`
- Quoting: one unit → one blockquote + `path:`; no stitch; paraphrase labeled
- Strip `[[` `]]` highlight markers when pasting quotes

## GitHub
```bash
./gh.sh project view 1 --owner lakshaysethi2
./gh.sh project item-list 1 --owner lakshaysethi2
./gh.sh project item-list 1 --owner lakshaysethi2 | head -n 50
```

**`item-list` IS allowed** — an earlier "allowlist miss" was caused by `2>&1` in
the command, not by the subcommand. Rules:
- **Never use `2>&1`** in exec commands — it makes the whole command an allowlist
  miss. Tool stderr is captured automatically.
- Pipes are fine with allowlisted bins: `| head -n N`, `| tail -n N`, `| cat`,
  `| jq '...'`. Use `head -n N` (not `head -N`).
- Keep the repo/owner flags: `1 --owner lakshaysethi2`.

## TTS / Giphy
```bash
./tts.py "verbatim from one unit" [voice]
./giphy.py "term"    # MEDIA:/tmp/openclaw/media/...
```

## Memory
`memory_search` or `./bin/rg -n "kw" MEMORY.md memory/`

## Exec allowlist
```bash
./search.py "phrase" 10
```
Single plain command. Prefer no pipes. Real errors are text — never invent “image attachment” failures.
