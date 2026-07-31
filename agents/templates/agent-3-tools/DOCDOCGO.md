# DOCDOCGO.md — Search only + perfect quoting

**You may only use** `GET https://docdocgo.lak.nz/api/search` via `./search.py`.  
Do **not** call `/api/read`, `/api/rag`, or `/api/files`.

Field guide: https://github.com/friend-bot-dnd/docdocgo-api-guide

---

## HARD QUOTE RULES (non-negotiable)

1. **Single-source quotes** — Each Discord **blockquote** comes from **exactly one** search unit (`SOURCE_PATH`). Never stitch two paths into one quote.
2. **Always print the source** — Under every quote: display title + `path: \`SOURCE_PATH\``.
3. **Verbatim-only for quotes** — Quote text must be **verbatim** from that unit’s `VERBATIM:` block (drop leading/trailing `…` and `[[` `]]` highlight markers). Do not reorder or blend.
4. **Paraphrase must be labeled** — Own wording → prefix **`paraphrase:`**. Never put paraphrase in a quote block.
5. **Context** — Members asked for fuller context: use `-c 900 -w 600` for teaching/batched quotes so each quote carries real context, not a 1-line fragment.
6. **1–3 quotes max** per reply; each its own blockquote + path.

### Correct pattern
```
> …verbatim from unit 2 only…

— Along The Path To Enlightenment  
path: `Along_the_Path_to_Enlightenment_...`
```

### Forbidden
- Stitched multi-book quotes
- Rewrites presented as quotes
- Missing path under a quote
- Invented Hawkins lines
- Claiming search returned “images/attachments” when output is plain text (it is always plain text)

---

## Always search first (HARD GATE)

For spiritual / Hawkins / ACIM / consciousness / quote questions — and ANY content
question with a correct answer:

1. Run `./search.py` **≥2 times before your first answer** (different phrasings /
   synonyms / filters). Minimum **1 search, never zero** — even when you're sure
   you know the answer. Grounding beats memory.
2. Prefer a **real phrase** over loose single words.
3. **Empty result → rephrase and search again** (synonyms, `lectures`,
   `all-hawkins-books`). One miss is not permission to answer from memory.
4. Answer only from returned units.
5. Match center may show `[[phrase]]` inside VERBATIM — strip markers when quoting.

---

## Command

```bash
./search.py "query" [limit] [filter] [options]
```

| Arg / flag | Default | Notes |
|---|---|---|
| `query` | required | ≥4 chars |
| `limit` | **10** (min, default; max 25) | **Never request fewer than 10** — tool floors to 10 |
| `filter` | `all` | `all` · `books` · `all-hawkins-books` · `lectures` · exact path |
| `-p N` | 1 | Page |
| `-c N` | **350** | API snippet padding (**min 250**) |
| `-w N` | **260** | Max chars shown in VERBATIM around match |
| `-g N` | server 250 | Optional groupDistance |
| `--partial` | off | wholeWords=false |
| `--full` | off | Full API snippet for that **one** unit |
| `--json` | off | Raw payload |

### Default pattern
```bash
./search.py "<their phrase>" 10
./search.py "<synonym / Hawkins term>" 10 all-hawkins-books
./search.py "<topic>" 10 lectures -c 500 -w 300
```

Prefer **limit 10** — never request fewer than 10 (tool floors to 10).

## Quote batches + TTS (member expectation)
- **"N quotes" / "more quotes" → deliver N quotes** (verbatim, each with
  `path:`). One search (limit 10) returns ≥10 units; pull page 2 or more
  phrasings until you have N. Never stop at 2–3.
- Quote with **real context**: `./search.py "<phrase>" 10 -c 900 -w 600`.
- **Text + TTS together**: attach `./tts.py "<verbatim text>"` for the focal
  quote. No TTS = incomplete delivery when quotes were asked for.

---

## Tool output shape (plain text — not images)

```
--- UNIT N ---
SOURCE_PATH: …
DISPLAY: …
VERBATIM:
…trimmed text with optional [[match]] …
CITE: — Title
path: `SOURCE_PATH`
--- END UNIT N ---
```

Treat units as sealed packages. Output is always UTF-8 text in the exec tool result.

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

## Exec allowlist
Run search as a **single plain command**:
```bash
./search.py "phrase" 10
```
No pipes needed. Do **not** invent “allowlist is broken” or “image attachments” without a real error string from the tool.
