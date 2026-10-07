# Translation Technique workbench — how the numbers are made

Route `/translation-technique` (private preview, phrase-gated). Data in `data/tt/`, versioned by `data/tt/VERSION`.

## Pipeline
1. **Lemma layer** (`scripts/tt_build_lemmas.py`): each Peshitta OT token → normalized form → SEDRA IV lookup (cached in `data/tt/sedra_cache.json`) → affix rules on a miss → model proposal on a second miss. Source tag per token: `sedra | rule | model | unresolved`. Coverage per book in `data/tt/lemmas/coverage.json`.
2. **Alignment** (`scripts/tt_align.py`): IBM Model 1 both directions with a diagonal prior over all shared MT–Peshitta verses, symmetrized (intersection + grow-diag). Ambiguous SEDRA analyses are chosen by the alignment. Links under the threshold are listed in `pending.json` for model adjudication (`scripts/tt_adjudicate.py links`), each tagged `source: model`. `manifest.json` records versions, threshold, model id, link counts and a SHA-256 of the alignment files; the page prints that hash.
3. **Tables** (`translation_technique/tables.py`): distribution, cross-tabulation by BHSA features (`vs, vt, clause_typ, obj_function, next_prep, book`), chi-square with a reliability flag, Cramér's V, model share. No model at query time.
4. **Witnesses** (`data/tt/witnesses/`): hand-keyed alternative readings with sigla and a required `keyed_from`. Tables can be rerun per witness. No readings are taken from the Leiden edition.
5. **Evaluation** (`scripts/tt_eval_gold.py`): 200-verse Deuteronomy sample, two readers (owner, model), aligner precision/recall on the agreed subset. Printed on the page; "unevaluated" until it exists.

## Rebuilding
`tt_build_lemmas.py --all` (offline after the first run) → `tt_align.py` → optional `tt_adjudicate.py` → `tt_eval_gold.py eval`. Bump `data/tt/VERSION` on any change to rules, threshold or corpus.
`tt_adjudicate.py` accepts `--max-batches N` (stop after N batches, any mode) and prints `model=<id> batches=<n> accepted=<k>` at the end of every run.

## Scope of the model adjudication
Model adjudication (lemma proposals, pending links, the model-as-second-reader gold rows) has been run for **Deuteronomy only**. No model-sourced tokens or links exist outside Deuteronomy. Lemma and alignment coverage of other books is whatever `data/tt/lemmas/coverage.json` and the `books` list in `data/tt/align/manifest.json` show at any time (the whole-OT lemma build is in progress; aligning the other books is a follow-up). Model-share figures are therefore zero outside Deuteronomy. Extending it is a per-book decision and a per-book cost.

## Known limits
SEDRA coverage of hapax forms is about half before normalization. Free renderings and idioms get low link probabilities and stay visible in the occurrence list. Animacy and other semantic facets are not available in version one. Model lemma answers are applied per surface form (normalized), so homographs share one answer: if two different words have the same consonantal form, both tokens receive the lemma the model chose for the first context it saw.
