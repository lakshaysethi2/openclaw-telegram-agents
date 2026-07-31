# TOOLS.md — Friend Bot

## docdocgo (PRIMARY — search only)
```bash
./search.py "query" [limit] [filter]
./search.py "nothing is causing anything" 3
./search.py "surrender" 3 all-hawkins-books
./search.py "forgiveness" 3 lectures -c 500 -w 300
./search.py "ego" 3 --partial
```
- Endpoint: **only** `GET https://docdocgo.lak.nz/api/search`
- Output = plain-text **UNITs** (one `SOURCE_PATH` each) — **never images**
- Default **limit=3** (honored exactly; max 15)
- Guide: `DOCDOCGO.md` · https://github.com/friend-bot-dnd/docdocgo-api-guide
- Do **not** call `/api/read`, `/api/rag`, `/api/files`
- Quoting: one unit → one blockquote + `path:`; no stitch; paraphrase labeled
- Strip `[[` `]]` highlight markers when pasting quotes

## GitHub
```bash
./gh.sh project view 1 --owner lakshaysethi2
```

## TTS / Giphy
```bash
./tts.py "verbatim from one unit" [voice]
./giphy.py "term"    # MEDIA:/tmp/openclaw/media/...
```

## Memory
`memory_search` or `./bin/rg -n "kw" MEMORY.md memory/`

## Exec allowlist
```bash
./search.py "phrase" 3
```
Single plain command. Prefer no pipes. Real errors are text — never invent “image attachment” failures.
