# TOOLS.md — Friend Bot local tools

## docdocgo (PRIMARY)
```bash
./search.py "query" 5
./search.py "exact teaching phrase" 5 --expand
./read.py PATH -q "phrase"
./rag.py "natural language question" 3
```
- Craft guide: `DOCDOCGO.md`
- Upstream: https://github.com/friend-bot-dnd/docdocgo-api-guide
- `read` is **windowed only** (no full-file dumps)
- If snippets look like WEBVTT intros → `--expand` or `./read.py`

## GitHub CLI
```bash
./gh.sh project view 1 --owner lakshaysethi2
./gh.sh project item-list 1 --owner lakshaysethi2 --limit 20
```

## TTS
```bash
./tts.py "text" [voice]    # → MEDIA:/tmp/openclaw/media/...
```

## Giphy
```bash
./giphy.py "term"          # → MEDIA:/tmp/openclaw/media/...gif
```

## Memory
```bash
# memory_search tool, or:
./bin/rg -n "kw" MEMORY.md memory/
```

## Exec policy
Allowlisted paths only. Prefer `./search.py`, `./read.py`, `./rag.py`, `./tts.py`, `./giphy.py`, `./gh.sh`.
