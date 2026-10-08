# Peshiṭta Correspondences (route `/translation-technique`) — how the numbers are made

Route `/translation-technique` (unlisted: not linked from the site, `noindex`; reachable by URL). Data in `data/tt/`, versioned by `data/tt/VERSION`.

For the methodology and its scholarly sources, see [methodology-peshitta-correspondences.md](methodology-peshitta-correspondences.md).

## Pipeline
1. **Lemma layer** (`scripts/tt_build_lemmas.py`): each Peshitta OT token → normalized form → SEDRA IV lookup (cached in `data/tt/sedra_cache.json`) → affix rules on a miss → model proposal on a second miss. Source tag per token: `sedra | rule | model | unresolved`. Coverage per book in `data/tt/lemmas/coverage.json`.
2. **Alignment** (`scripts/tt_align.py`): IBM Model 1, the classic statistical word-alignment method, both directions with a diagonal prior over the verses of the books listed in `manifest.json` (currently Deuteronomy), symmetrized (intersection + grow-diag). Ambiguous SEDRA analyses are chosen by the alignment. Links under the threshold are listed in `pending.json` for model adjudication (`scripts/tt_adjudicate.py links`), each tagged `source: model`. `manifest.json` records versions, threshold, model id, link counts and a SHA-256 of the alignment files; the page prints that hash.
3. **Tables** (`translation_technique/tables.py`): distribution, cross-tabulation by BHSA features (`vs, vt, clause_typ, obj_function, next_prep, book`), chi-square with a reliability flag, Cramér's V, model share. No model at query time.
4. **Witnesses** (`data/tt/witnesses/`): hand-keyed alternative readings with sigla and a required `keyed_from`. Tables can be rerun per witness. An optional `heb_lex` links a witness token to the otherwise unaligned Hebrew word it renders. No readings are taken from the Leiden edition.
5. **Evaluation** (`scripts/tt_eval_gold.py`): 200-verse Deuteronomy sample, two readers (owner, model), aligner precision/recall on the agreed subset. Printed on the page; "unevaluated" until it exists.

## Rebuilding
`tt_build_lemmas.py --all` (offline after the first run) → `tt_align.py` → optional `tt_adjudicate.py` → `tt_eval_gold.py eval`. Bump `data/tt/VERSION` on any change to rules, threshold or corpus.
Rebuild order: `tt_build_lemmas.py` → `tt_adjudicate.py lemmas` (refreshes `coverage.json` and `unresolved.<book>.json`) → `tt_align.py` → `tt_adjudicate.py links` → `tt_eval_gold.py eval`. Running `tt_align.py --books <subset>` merges into `manifest.json`, `lexemes.json` and `pending.json`: only the named books are replaced. `tt_align.py` refuses to overwrite an `align/<book>.jsonl` that holds `source: model` rows (paid adjudications) and prints how many would be lost; `--force` overrides it deliberately, after which lemmas and links must be adjudicated again. `scripts/tt_repair_align.py <book>` repairs an adjudicated file offline (orphaned Syriac tokens, link kinds, null `prob` on model links) and refreshes the manifest.
`tt_adjudicate.py` accepts `--max-batches N` (stop after N batches, any mode) and prints `model=<id> batches=<n> accepted=<k>` at the end of every run.

## Scope of the model adjudication
Model adjudication (lemma proposals, pending links, the model-as-second-reader gold rows) has been run for **Deuteronomy only**. No model-sourced tokens or links exist outside Deuteronomy. Lemma and alignment coverage of other books is whatever `data/tt/lemmas/coverage.json` and the `books` list in `data/tt/align/manifest.json` show at any time (the whole-OT lemma build is in progress; aligning the other books is a follow-up). Model-share figures are therefore zero outside Deuteronomy. Extending it is a per-book decision and a per-book cost.

## Known limits
SEDRA coverage of hapax forms is about half before normalization. Free renderings and idioms get low link probabilities and stay visible in the occurrence list. Animacy and other semantic facets are not available in version one. Model lemma answers are applied per surface form (normalized), so homographs share one answer: if two different words have the same consonantal form, both tokens receive the lemma the model chose for the first context it saw.
