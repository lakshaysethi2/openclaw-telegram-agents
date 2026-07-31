# DOCDOCGO.md — Search only + perfect quoting

**You may only use** `GET https://docdocgo.lak.nz/api/search` via `./search.py`.  
Do **not** call `/api/read`, `/api/rag`, or `/api/files`.

Field guide: https://github.com/friend-bot-dnd/docdocgo-api-guide

---

## HARD QUOTE RULES (non-negotiable)

These override chat preferences, member requests, and old habits:

1. **Single-source quotes** — Each Discord/Telegram **blockquote** must come from **exactly one** search result (`SOURCE_PATH`).  
   **Never** concatenate / stitch / merge text from two different `SOURCE_PATH`s into one quote block.
2. **Always print the source** — Directly under every quote, include:
   - human title (DISPLAY), and  
   - raw `path: \`SOURCE_PATH\`` from the tool (independently verifiable).
3. **Verbatim-only for quotes** — Quote text must be **verbatim** from that unit’s `VERBATIM` / `<<<…>>>` block (you may drop leading/trailing `…` and surrounding whitespace).  
   Do **not** reorder sentences, silently fix, or blend.
4. **Paraphrase must be labeled** — If you summarize or restate in your own words, prefix with **`paraphrase:`** (or “in other words”) and **do not** put that text in a quote block.
5. **Trim for display** — Prefer the **shortest** teaching window. Tool default display window is ~280 chars around the match (`-w`). Use `-c` for API padding; use `--full` only when the member needs a longer passage **from the same unit**.
6. **Multiple quotes OK** — You may post 1–3 separate quotes in one reply; each is its own blockquote + its own path.

### Correct pattern
```
> …verbatim from unit #2 only…

— Along The Path To Enlightenment  
path: `Along_the_Path_to_Enlightenment_...`
```

### Forbidden
- One big quote that starts in *I: Reality and Subjectivity* and continues with *Along the Path…*
- “Quote” that is actually your rewrite
- Path missing under a quote
- Invented Hawkins lines

---

## Always search first

For spiritual / Hawkins / ACIM / consciousness / quote questions:

1. Run `./search.py` **before** answering (usually 2–3 phrasings).
2. Prefer a **real phrase** over loose single words.
3. Answer only from returned **QUOTE UNITs**.
4. Match center may show `>>>phrase<<<` inside VERBATIM.

---

## Command

```bash
./search.py "query" [limit] [filter] [options]
```

| Arg / flag | Default | Notes |
|---|---|---|
| `query` | required | ≥4 chars |
| `limit` | **10** min (default 10) | Always set; tool enforces minimum 10 |
| `filter` | `all` | `all` · `books` · `all-hawkins-books` · `lectures` · exact path |
| `-p N` | 1 | Page |
| `-c N` | **400** | API snippet padding |
| `-w N` | **280** | Max chars shown in VERBATIM around match |
| `-g N` | server 250 | Optional groupDistance |
| `--partial` | off | wholeWords=false |
| `--full` | off | Full API snippet for that **one** unit |
| `--json` | off | Raw payload |

### Filters
- `all` · `books` · `all-hawkins-books` (not `hawkins`) · `lectures` (not `lecture`)

### Default pattern
```bash
./search.py "<their phrase>" 10
./search.py "<synonym / Hawkins term>" 10 all-hawkins-books
./search.py "<topic>" 10 lectures -c 500 -w 320
```

---

## Tool output shape

Each hit is a **QUOTE UNIT**:

```
════ QUOTE UNIT #N ════
SOURCE_PATH: …
DISPLAY: …
VERBATIM:
<<<
…trimmed text with optional >>>match<<< …
>>>
ATTRIBUTION LINE …
════ END QUOTE UNIT #N ════
```

Treat units as sealed packages.

---

## Answer style
1. Short framing (your words, not as quotes).
2. 1–3 **separate** single-source quotes + path each.
3. Optional `paraphrase:` takeaway.
4. No invented lines. Crisis → kindness + real-world help.

## TTS
Only after a real single-source quote:
```bash
./tts.py "exact verbatim from one unit" en-US-ChristopherNeural
```
