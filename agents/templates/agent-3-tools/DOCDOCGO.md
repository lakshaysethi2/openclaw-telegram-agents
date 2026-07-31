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
5. **Trim** — Prefer the shortest teaching window. Default tool window ~260 chars. Use `--full` only for a longer passage from the **same** unit.
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

## Always search first

For spiritual / Hawkins / ACIM / consciousness / quote questions:

1. Run `./search.py` **before** answering (usually 2–3 phrasings).
2. Prefer a **real phrase** over loose single words.
3. Answer only from returned units.
4. Match center may show `[[phrase]]` inside VERBATIM — strip markers when quoting.

---

## Command

```bash
./search.py "query" [limit] [filter] [options]
```

| Arg / flag | Default | Notes |
|---|---|---|
| `query` | required | ≥4 chars |
| `limit` | **3** (max 15) | **Honored exactly** — use 3 unless you need more |
| `filter` | `all` | `all` · `books` · `all-hawkins-books` · `lectures` · exact path |
| `-p N` | 1 | Page |
| `-c N` | **350** | API snippet padding |
| `-w N` | **260** | Max chars shown in VERBATIM around match |
| `-g N` | server 250 | Optional groupDistance |
| `--partial` | off | wholeWords=false |
| `--full` | off | Full API snippet for that **one** unit |
| `--json` | off | Raw payload |

### Default pattern
```bash
./search.py "<their phrase>" 3
./search.py "<synonym / Hawkins term>" 3 all-hawkins-books
./search.py "<topic>" 3 lectures -c 500 -w 300
```

Prefer **limit 3**. Do not request 10 unless paging intentionally.

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
./search.py "phrase" 3
```
No pipes needed. Do **not** invent “allowlist is broken” or “image attachments” without a real error string from the tool.
