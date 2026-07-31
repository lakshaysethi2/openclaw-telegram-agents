# DOCDOCGO.md — Search only

**You may only use** `GET https://docdocgo.lak.nz/api/search` via `./search.py`.  
Do **not** call `/api/read`, `/api/rag`, or `/api/files`.

Field guide: https://github.com/friend-bot-dnd/docdocgo-api-guide

---

## Always search first

For spiritual / Hawkins / ACIM / consciousness / quote questions:

1. Run `./search.py` **before** answering (usually 2–3 different phrasings).
2. Prefer a **real phrase** (`"nothing is causing anything"`) over loose single words.
3. Quote only returned snippets. Attribute with `path` (+ chapter when shown).
4. Match center is marked `>>>phrase<<<` when the API snippet contains the query.

---

## Command

```bash
./search.py "query" [limit] [filter] [options]
```

| Arg / flag | Default | Notes |
|---|---|---|
| `query` | required | ≥4 chars. Multi-word ranked search |
| `limit` | 5 | Always set (API bare default is 100) |
| `filter` | `all` | `all` · `books` · `all-hawkins-books` · `lectures` · exact path |
| `-p N` | 1 | Page (deterministic) |
| `-c N` | **400** | Snippet padding around the match anchor |
| `-g N` | server 250 | Optional `groupDistance` (how close words must be to group) |
| `--partial` | off | `wholeWords=false` |
| `--full` | off | Don’t locally truncate display |
| `--json` | off | Raw payload |

### Filters (case-sensitive; bad values empty or warn)
- `all` · `books` · `all-hawkins-books` (not `hawkins`) · `lectures` (not `lecture`)

---

## How search works (so you use it well)

1. Query words (minus light stop-words) are found across the library.
2. Nearby hits are **grouped** if consecutive hits are within `groupDistance` (default **250** chars). This is **independent** of `-c` context padding.
3. Each result snippet is **centered on**:
   - the **exact query phrase** when present near the group, else
   - the **densest cluster** of query keywords
4. Then `context` chars of padding are added on each side.
5. Scoring favors more unique keywords + tight proximity; **exact phrase ×1.5**.

### Practical tips
- Use full teaching phrases when you know them.
- Raise `-c` for longer quotes (400–800 is fine). Grouping no longer blows up with large context.
- If empty: synonym, `--partial`, or `filter all`.
- `total_pages` is real page count (`ceil(matches/limit)`).
- `match_text` = unique keywords in the group (not every span).
- Prefer page 1; use `-p 2` only when page 1 is useful.

### Default pattern
```bash
./search.py "<their phrase>" 5
./search.py "<synonym / Hawkins term>" 5 all-hawkins-books
./search.py "<topic>" 5 lectures -c 500
# thin results:
./search.py "<simpler word>" 5 --partial
```

---

## Answer style
1. 1–3 sentences grounded in snippets.
2. 1–3 short quotes with path attribution.
3. No invented Hawkins lines.
4. Crisis → kindness + real-world help.

## TTS after a good short quote
```bash
./tts.py "exact quote" en-US-ChristopherNeural
```
