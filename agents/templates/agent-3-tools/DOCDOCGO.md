# DOCDOCGO.md — Primary knowledge tools

Source field guide: https://github.com/friend-bot-dnd/docdocgo-api-guide  
Base: `https://docdocgo.lak.nz`

You have **three** tools. Prefer them in this order for teaching questions.

| Tool | Endpoint | Use for |
|---|---|---|
| `./search.py` | `GET /api/search` | Find sources + short quotes |
| `./search.py ... --expand` or `./read.py` | `GET /api/read/:path` (windowed only) | Full paragraph around the real match |
| `./rag.py` | `POST /api/rag` | Semantic ~500-token chunks when keyword search is thin |

**Never** dump whole files into Discord. `read.py` always windows. Do not call `/api/files` browsing dumps.

---

## Always search first

For spiritual / Hawkins / ACIM / consciousness / quote questions:

1. Run tools **before** answering (usually 2–3 queries).
2. Prefer a **real phrase** (`"nothing is causing anything"`) over loose words.
3. If snippets look like lecture intros / WEBVTT banter → **`--expand`** (or `./read.py PATH -q "..."`).
4. Quote only tool text. Attribute with `path` (+ chapter when shown).
5. Optional TTS after a short exact quote.

---

## Commands

### Keyword search
```bash
./search.py "query" [limit] [filter] [options]
```

| Arg / flag | Default | Notes |
|---|---|---|
| `query` | required | Prefer ≥4 chars and a real phrase |
| `limit` | 5 | Set explicitly |
| `filter` | `all` | `all` · `books` · `all-hawkins-books` · `lectures` · exact path |
| `-p N` | 1 | Pagination |
| `-c N` | **300** | API context. **Do not use 1200+** for multi-word search — it groups distant hits and looks like file-start junk |
| `--expand` | off | Re-center each hit via `/api/read` on exact phrase / densest terms |
| `--before` / `--after` | 500 / 1000 | Expand window |
| `--max-chars` | 3500 | Cap expanded passage |
| `--full` | off | Don’t locally truncate API snippets |
| `--partial` | off | `wholeWords=false` |
| `--json` | off | Debug |

### Windowed read (when you already have a path)
```bash
./read.py PATH -q "exact phrase"
./read.py PATH -o OFFSET -q "phrase"
./read.py PATH -o OFFSET          # offset window only
```

### Semantic RAG
```bash
./rag.py "natural language question" 3
```

---

## Critical: sparse snippets

The search API uses `context` both for padding **and** for grouping multi-word hits.  
Large `-c` (e.g. 1200) can chain `"is"` at file start with `"causing"` thousands of chars later → WEBVTT intro garbage.

**Fix:**
```bash
./search.py "nothing is causing anything" 5 --expand
# or
./read.py Some_Lecture_Path -q "nothing is causing anything"
./rag.py "nothing is causing anything" 3
```

The tool marks `⚠️ SPARSE` and prints the expand command when proximity is huge.

Match center is marked with `>>>phrase<<<`.

---

## Default pattern for a member question
```bash
./search.py "<their key phrase>" 5 --expand
./search.py "<synonym>" 5 all-hawkins-books --expand
# if still thin:
./rag.py "<question in plain words>" 3
./search.py "<simpler word>" 5 --partial
```

### Filters (case-sensitive; typos silent-empty)
| Value | Use |
|---|---|
| `all` | Default |
| `books` | Books |
| `all-hawkins-books` | Hawkins books only (NOT `hawkins`) |
| `lectures` | Lectures (NOT `lecture`) |
| exact path | From a prior hit |

---

## Answer style (Discord)
1. 1–3 sentence plain answer grounded in results.
2. 1–3 short quotes with attribution (`path` / title).
3. Prefer expanded / RAG passages over junk intros.
4. Crisis → kindness + real-world help.

### Never
- Invent quotes.
- Paste whole books.
- Claim the library is empty after one bad filter.
- Use giant `-c` instead of `--expand`.

---

## TTS companion
```bash
./tts.py "exact quote text" en-US-ChristopherNeural
```
Media only under `/tmp/openclaw/media/`.
