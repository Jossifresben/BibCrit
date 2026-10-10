# Peshiṭta Correspondences — SQLite store and data releases

**Date:** 2026-10-10
**Status:** approved design, not yet implemented
**Extends:** `2026-10-07-translation-technique-design.md` (the workbench itself; its hard constraints all still apply)

## 1. Why

The workbench holds every alignment row of every exposed book in memory for the life of the process. Deuteronomy alone costs about 34 MB after compaction; the whole Old Testament (39 books, 478,950 rows) would cost about 1.2 GB. The Render instance has 512 MB and sits at about 44% with Deuteronomy loaded. The whole-OT alignment therefore cannot go live on the current store.

This design moves the rows into a SQLite file read from local disk, so memory no longer depends on how many books are exposed, and defines how data versions are published without growing the git history.

**Success criteria**

- Memory of the web process stays within 30 MB of its no-data baseline whatever books are exposed and whatever query is run.
- Every number the page shows for Deuteronomy is identical to today's, verified by a test that runs both stores over the same data.
- URLs, JSON shapes, the page and the i18n keys do not change.
- The other 38 books are present in the data but not reachable from the page or the API until the owner changes one setting.
- Git history grows by a few lines per data version, never by the data.

**Unchanged constraints**: no model produces a number; no model at query time; counting stays in `translation_technique/tables.py`; everything versioned and hashed.

## 2. Decision record

Options weighed, in the order they were rejected:

| Option | Rejected because |
|---|---|
| Commit gzipped JSONL per book (~12 MB for 39 books) and build SQLite at deploy | Every data version adds ~12 MB to a public repo's history; the aligner will be retuned many times once a gold standard exists. Owner: "no go". |
| Commit the SQLite file | Same problem, ~72 MB per version. |
| Supabase (Postgres the site already uses) | Every query over the network; rows take a large share of the free tier; the data has no citable, versioned form. |
| DuckDB / Parquet | Heavy dependency, more memory, no benefit at 480k rows. |
| One pre-split file per lexeme | The consistency histograms need every lexeme of the selected books; that is a database query. |
| Download from Zenodo at build time | Same as the chosen option but the deploy fails when the download fails and Zenodo has no API for "latest file of a concept DOI" that is simple to script. |

**Chosen:** one SQLite file per data version, attached to a GitHub release on `Jossifresben/BibCrit` tagged `tt-data-<version>`; the repo commits only a small release manifest; the server downloads, verifies and opens the file at start. Deuteronomy's JSONL stays committed as the fallback.

Side effects accepted: each data version is a public, permanent download (release notes say "unevaluated, provisional" until the gold evaluation exists); with Zenodo's GitHub integration switched on by the owner, each release gets its own DOI.

## 3. Data flow

```
scripts/tt_align.py ──▶ data/tt/align/<book>.jsonl (local, 39 books; only deuteronomy.jsonl committed)
                                 │
scripts/tt_build_db.py ──▶ data/tt/db/tt-<version>.sqlite  (+ .gz, sha256)     [gitignored]
                                 │
scripts/tt_release.py ──▶ GitHub release tt-<version>, asset tt-<version>.sqlite.gz
                       ──▶ data/tt/release.json                                 [committed]
                                 │
server start (gunicorn post_fork, or app._init) ──▶ translation_technique.db.ensure_db()
      downloads if missing, verifies sha256, gunzips, atomic rename ──▶ data/tt/db/tt-<sha12>.sqlite
                                 │
TTStore ──▶ SqliteBackend (if the file for release.json's sha256 is present and its meta matches)
        ──▶ JsonBackend   (otherwise: today's per-book JSONL reader, Deuteronomy only)
```

## 4. Files

### 4.1 `data/tt/release.json` (committed)

```json
{
  "version": "0.2.0",
  "url": "https://github.com/Jossifresben/BibCrit/releases/download/tt-data-0.2.0/tt-0.2.0.sqlite.gz",
  "sha256": "<sha256 of the gunzipped .sqlite>",
  "sha256_gz": "<sha256 of the .gz as downloaded>",
  "size_gz": 18900000,
  "built_at": "2026-10-10T12:00:00+00:00",
  "align_hash": "<manifest.hash of the alignment the file was built from>",
  "books": 39,
  "rows": 478950
}
```

`version` is `data/tt/VERSION` at build time. `align_hash` is the alignment manifest hash already printed on the page, so the page keeps printing the same provenance.

### 4.2 The SQLite file

Built by `scripts/tt_build_db.py` from `data/tt/align/*.jsonl` and `data/tt/lexemes.json`. `PRAGMA journal_mode=OFF, page_size=4096`; opened read-only by the app (`?mode=ro`, `check_same_thread=False`, one connection per thread via `threading.local`).

```sql
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
-- version, align_hash, built_at, books (comma list), rows

CREATE TABLE link (
  book          TEXT NOT NULL,     -- stem, e.g. 'deuteronomy'
  ref           TEXT NOT NULL,     -- 'Deuteronomy 22:4'
  chapter       INTEGER NOT NULL,
  verse         INTEGER NOT NULL,
  heb_node      INTEGER,           -- NULL for Syriac-only rows
  heb_lex       TEXT,
  heb_word      TEXT,
  heb_gloss     TEXT,
  sp TEXT, vs TEXT, vt TEXT, clause_typ TEXT, obj_function TEXT, next_prep TEXT,
  syr_position  INTEGER,
  syr_lemma     TEXT,
  syr_source    TEXT,
  prob          REAL,              -- NULL for model-adjudicated links
  kind          TEXT NOT NULL,
  source        TEXT NOT NULL
);
CREATE INDEX ix_link_lex  ON link (heb_lex, book);
CREATE INDEX ix_link_ref  ON link (book, chapter, verse);
CREATE INDEX ix_link_sp   ON link (sp, book) WHERE kind != 'null' AND syr_lemma IS NOT NULL;

CREATE TABLE lexeme (
  lex TEXT NOT NULL, book TEXT NOT NULL, count INTEGER NOT NULL,
  word TEXT, gloss TEXT, PRIMARY KEY (lex, book)
);
```

`heb_feats` is flattened into six columns and rebuilt into the nested dict on read, so `tables.py` sees exactly the row shape of spec §5.2. Rows with `heb_feats: null` read back as `None`. Row order within a verse is `(chapter, verse, rowid)`, i.e. file order, which is what the JSON reader gives today.

Measured on the 39-book local data: 72 MB on disk, 18 MB gzipped, 3 s to build.

### 4.3 Local cache

`data/tt/db/` is gitignored. The opened file is `data/tt/db/tt-<sha256[:12]>.sqlite`, named by the manifest's `sha256`, so a new release never collides with an old cache and old files can be deleted on sight. Downloads go to `<name>.part` and are renamed only after the checksum passes.

## 5. Modules

### 5.1 `translation_technique/db.py` (new; no Flask)

- `build(align_dir, lexemes_path, out_path, version) -> dict` — streams each `*.jsonl` line by line into `link`, `lexemes.json` into `lexeme`, writes `meta`, creates indexes, `VACUUM`s, returns `{rows, books, sha256, size}`.
- `ensure_db(tt_dir, timeout=120) -> str | None` — reads `release.json`; if the target file exists with a matching `meta.align_hash`, returns its path at once. Otherwise, under `fcntl.flock` on `data/tt/db/.lock`, downloads with `urllib` (timeout, `BIBCRIT_TT_RELEASE_URL` env override for mirrors/tests), verifies `sha256_gz`, gunzips to `.part` while hashing, verifies `sha256`, renames. Any failure logs one line and returns `None`; nothing raises into the caller.
- `open_ro(path) -> sqlite3.Connection`.

### 5.2 `translation_technique/store.py`

`TTStore` keeps its public interface and gains a backend. On construction it calls `ensure_db` (cheap when the file is present) and picks `SqliteBackend` if a path comes back, else `JsonBackend` (the current code, moved intact, including `_read_compact`). `store.backend_name` is `'sqlite:<version>'` or `'json'` and is shown in the page footer next to the hash.

Interface changes, all additive:

| Method | Today | After |
|---|---|---|
| `books` | manifest books | books in the backend **∩ visible books** (§6) |
| `rows(books)` | all rows of the books | unchanged signature; SqliteBackend raises `TooManyRows` if the selection exceeds `ROW_CAP = 60_000` so no caller can load the corpus by accident |
| `rows_for_lex(books, lex, refs=())` | — | rows where `heb_lex = lex` **or** `ref IN refs`, for the selected books; `lex=None` means refs only. `refs` are the witness's verse refs, so `apply_witness` still finds the Syriac-only row it needs for an asserted link |
| `verse_rows(ref)` | filter one book | `WHERE book=? AND chapter=? AND verse=?` |
| `spread_groups(books, sp, exclude_refs=())` | — | `SELECT heb_lex, syr_lemma, COUNT(*), SUM(is_model) … GROUP BY heb_lex, syr_lemma` over non-null linked rows of part of speech `sp`, excluding the given refs |
| `lexemes(q, books)` | scan `lexemes.json` | `SELECT … FROM lexeme WHERE book IN visible` then the same Python ranking as today (exact-stem first, then count); JsonBackend unchanged |

### 5.3 `translation_technique/tables.py`

One addition, no change to existing functions:

- `spread_from_groups(groups, sp, min_occ) -> dict` — the same histogram, examples and `model_share` as `spread()`, computed from `(heb_lex, syr_lemma, n, n_model)` groups. `spread()` is kept and re-expressed as `spread_from_groups(group_rows(rows, …))` so the two can be tested against each other.

Witness handling for the histograms: `groups = store.spread_groups(books, sp, exclude_refs=witness_refs) + group_rows(apply_witness(store.rows_for_lex(books, None, refs=witness_refs), subs), sp)`. The second term is a few dozen rows.

### 5.4 `blueprints/translation_technique.py`

`_rows_for(store, books, witness)` becomes `_rows_for(store, books, witness, lex)` and calls `rows_for_lex`. The four callers (`tt_table`, `tt_csv`, verse view, `tt_spread`) pass the lexeme they already have; `tt_spread` uses the groups path. The gold editor keeps `verse_rows`. Nothing else changes.

### 5.5 `gunicorn.conf.py`

`post_fork` additionally calls `ensure_db(DATA_DIR/tt)` and logs the result, so the download happens before the worker accepts traffic. Render waits for the health check, so no visitor waits on it. `app._init` also calls `ensure_db` (idempotent) so `flask run` and tests behave the same.

### 5.6 Scripts

- `scripts/tt_build_db.py [--out PATH]` — builds `data/tt/db/tt-<version>.sqlite`, gzips it beside, prints rows, size and both checksums.
- `scripts/tt_release.py [--notes FILE] [--dry-run]` — `gh release create tt-data-<version> data/tt/db/tt-<version>.sqlite.gz --title … --notes-file …`, then writes `data/tt/release.json`. Refuses to run if the tag exists or the working tree has uncommitted changes under `data/tt/` other than `release.json`. Default notes state the alignment hash, model share, and "unevaluated, provisional: no gold-standard evaluation has been run on this version".

## 6. Visible books

`BIBCRIT_TT_BOOKS` env var: comma-separated stems, or `all`. Default `deuteronomy`. `store.books` is the intersection of what the backend holds and this list; `_books_arg()` already filters unknown books, so every endpoint ignores a hidden book silently (as it does today for a book that was never built). `render.yaml` sets it explicitly to `deuteronomy` so the whole-OT release can ship before the page shows it.

## 7. Failure modes

| Situation | Behaviour |
|---|---|
| `release.json` absent (local checkout, tests) | JsonBackend, as today |
| download fails or checksum mismatch | one log line; JsonBackend; page footer shows `json`; `/api/tt/meta` carries `"backend": "json"` so a monitor can notice |
| release file newer than the code expects (`meta.schema != SCHEMA_VERSION`) | treated as missing; JsonBackend |
| `rows()` over too many rows | `TooManyRows` → HTTP 400 with a message; cannot happen from the page since every page query is per lexeme or per verse |
| two workers / threads starting at once | file lock; the second waits then finds the file |

## 8. Testing

- `tests/test_tt_db.py`: build a SQLite file from the test fixture's JSONL; `rows_for_lex`, `verse_rows`, `lexemes` equal the JsonBackend's results row for row; `spread_from_groups(spread_groups(…))` equals `spread(rows, …)` with and without the 9a1 witness; `ensure_db` rejects a bad checksum and returns `None`; `ensure_db` with a `file://` URL (via the env override) downloads, verifies and opens.
- `tests/test_tt_equivalence.py` (runs only if `data/tt/align/deuteronomy.jsonl` exists, i.e. the real data): builds the Deuteronomy database into a temp dir and asserts, for every lexeme in `lexemes.json` with ≥ 20 occurrences and for every facet, that `summary`, `crosstab` and `occurrences` from both backends are equal; `spread` for `subs`, `verb`, `prep` × `min_occ` 1/2/5/10 equal; witness 9a1 equal.
- Memory check in `tests/test_tt_db.py`: with the 39-book fixture DB (synthetic, generated in the test, ~50k rows), `tracemalloc` peak of a table query is under 5 MB.
- Existing `tt_` integration tests unchanged and passing.

## 9. Owner steps after implementation

1. `python scripts/tt_build_db.py` on the 39-book local data; `python scripts/tt_release.py` (needs `gh auth`); commit `release.json`; push.
2. Set `BIBCRIT_TT_BOOKS=deuteronomy` in the Render dashboard (render.yaml has it, the dashboard may not follow it).
3. Optional: switch on the Zenodo–GitHub integration for the repo so `tt-data-*` releases get DOIs; add the DOI to the release notes afterwards.
4. When ready to expose more books: change `BIBCRIT_TT_BOOKS` and redeploy. Nothing else.

## 10. Out of scope

- Moving the lemma layer or SEDRA cache into the database (build inputs only).
- A "Deuteronomy vs rest of corpus" toggle on the page (next feature, needs §6 first).
- Displaying unresolved forms as "unresolved: form" rather than a blank rendering (separate fix, logged in the ledger).
