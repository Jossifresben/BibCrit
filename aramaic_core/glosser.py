"""Compositional word-level glossing for Syriac forms.

Composes glosses by combining root meaning with prefix/suffix semantics.
Supports manual overrides via word_glosses_override.json.
"""

import json
import os

from .affixes import generate_candidate_stems
from .characters import syriac_consonants_of


# --- Bilingual affix semantic maps ---
# These mirror the definitions in affixes.py but add EN/ES meanings.

PROCLITIC_GLOSSES = {
    # Single proclitics
    '\u0718':       {'en': 'and-', 'es': 'y-'},           # ܘ w-
    '\u0715':       {'en': 'of-', 'es': 'de-'},           # ܕ d-
    '\u0712':       {'en': 'in-', 'es': 'en-'},           # ܒ b-
    '\u0720':       {'en': 'to-', 'es': 'a-'},            # ܠ l-
    # Compound proclitics
    '\u0718\u0712': {'en': 'and.in-', 'es': 'y.en-'},     # ܘܒ wb-
    '\u0718\u0720': {'en': 'and.to-', 'es': 'y.a-'},      # ܘܠ wl-
    '\u0718\u0721': {'en': 'and.from-', 'es': 'y.de-'},   # ܘܡ wm-
    '\u0718\u0715': {'en': 'and.of-', 'es': 'y.de-'},     # ܘܕ wd-
    '\u0715\u0712': {'en': 'that.in-', 'es': 'que.en-'},  # ܕܒ db-
    '\u0715\u0720': {'en': 'that.to-', 'es': 'que.a-'},   # ܕܠ dl-
    '\u0715\u0721': {'en': 'that.from-', 'es': 'que.de-'},# ܕܡ dm-
    '\u0720\u0721': {'en': 'so.that-', 'es': 'para-'},    # ܠܡ lm-
}

VERBAL_PREFIX_GLOSSES = {
    '\u0710\u072C':             {'en': '[pass]', 'es': '[pas]'},     # ܐܬ Ethpeel
    '\u0710\u072B\u072C':       {'en': '[pass]', 'es': '[pas]'},     # ܐܫܬ Ettaphal (passive of Shafel)
    '\u072B':                   {'en': '[caus]', 'es': '[caus]'},    # ܫ Shafel causative
    '\u0721':                   {'en': '[ptcp]', 'es': '[part]'},    # ܡ participle
    '\u0722':                   {'en': '[impf]', 'es': '[impf]'},    # ܢ 3ms imperfect
    '\u072C':                   {'en': '[impf]', 'es': '[impf]'},    # ܬ 2ms/3fs imperfect
    '\u0710':                   {'en': '[impf]', 'es': '[impf]'},    # ܐ 1s imperfect / Aphel
}

SUFFIX_GLOSSES = {
    # Compound verbal + pronominal (longest first)
    '\u072C\u0718\u0722':       {'en': '-you(pl)', 'es': '-ustedes'},   # ܬܘܢ 2mp
    '\u072C\u071D\u0722':       {'en': '-you(fp)', 'es': '-ustedes'},   # ܬܝܢ 2fp
    '\u071D\u072C\u0717':       {'en': '-him', 'es': '-lo'},            # ܝܬܗ 3ms obj
    '\u0722\u0722':             {'en': '-we', 'es': '-nosotros'},       # ܢܢ 1cp

    # Pronominal suffixes
    '\u0717\u0718\u0722':       {'en': '-their', 'es': '-su(pl)'},      # ܗܘܢ 3mp
    '\u0717\u071D\u0722':       {'en': '-their(f)', 'es': '-su(fp)'},   # ܗܝܢ 3fp
    '\u071F\u0718\u0722':       {'en': '-your(pl)', 'es': '-su(uds)'},  # ܟܘܢ 2mp
    '\u071F\u071D\u0722':       {'en': '-your(fp)', 'es': '-su(uds)'},  # ܟܝܢ 2fp
    '\u0718\u0717\u071D':       {'en': '-her', 'es': '-su(f)'},         # ܘܗܝ 3fs
    '\u072C\u0717':             {'en': '-his', 'es': '-su'},            # ܬܗ 3ms poss
    '\u0722\u071D':             {'en': '-me', 'es': '-me'},             # ܢܝ 1s obj

    # Plural and state markers
    '\u0718\u072C\u0710':       {'en': '[abst]', 'es': '[abst]'},       # ܘܬܐ abstract
    '\u0718\u072C\u0717':       {'en': '[abst]-his', 'es': '[abst]-su'},# ܘܬܗ abstract+3ms
    '\u071D\u0722':             {'en': '[pl]', 'es': '[pl]'},           # ܝܢ plural
    '\u072C\u0710':             {'en': '[fem]', 'es': '[fem]'},         # ܬܐ feminine

    # Short pronominal
    '\u0717':                   {'en': '-his', 'es': '-su'},            # ܗ 3ms/3fs
    '\u071D':                   {'en': '-my', 'es': '-mi'},             # ܝ 1s poss
    '\u071F':                   {'en': '-your', 'es': '-tu'},           # ܟ 2ms poss
    '\u0722':                   {'en': '-them', 'es': '-los'},          # ܢ 3mp short

    # Verbal suffixes
    '\u0718':                   {'en': '[3pl]', 'es': '[3pl]'},         # ܘ 3mp perf
    '\u072C':                   {'en': '[perf]', 'es': '[perf]'},       # ܬ perfect
    '\u0710':                   {'en': '', 'es': ''},                   # ܐ emphatic (no label)
}


def _has_doubled_middle(stem: str, root_syriac: str) -> bool:
    """Check if stem has a doubled middle radical (R1-R2-R2-R3 pattern).

    In unvocalized Syriac, Pael forms sometimes show the middle radical
    written twice (e.g., ܡܠܠ mll). This heuristic catches those cases.
    """
    stem_consonants = syriac_consonants_of(stem)
    root_consonants = syriac_consonants_of(root_syriac)
    # Need exactly 4 stem consonants matching R1-R2-R2-R3 where R2 == root[1]
    if len(stem_consonants) == 4 and len(root_consonants) == 3:
        if (stem_consonants[0] == root_consonants[0] and
                stem_consonants[1] == root_consonants[1] and
                stem_consonants[2] == root_consonants[1] and
                stem_consonants[3] == root_consonants[2]):
            return True
    return False


def detect_verb_stem(prefixes_removed: list[str], suffixes_removed: list[str], stem: str, root_syriac: str) -> str | None:
    """Detect the Syriac verb stem based on prefix heuristics.

    Returns stem name or None if uncertain.
    Possible stems: Peal, Ethpeel, Pael, Ethpaal, Aphel, Shafel, Ettaphal
    """
    verbal_prefixes = set()
    for p in prefixes_removed:
        # Only consider verbal prefixes, not proclitics
        if p in VERBAL_PREFIX_GLOSSES:
            verbal_prefixes.add(p)

    # ܐܫܬ (Eshtaphal / Ettaphal)
    if '\u0710\u072B\u072C' in verbal_prefixes:
        return 'Ettaphal'

    # ܫ alone (Shafel causative)
    if '\u072B' in verbal_prefixes:
        return 'Shafel'

    # ܐܬ (Ethpeel or Ethpaal)
    if '\u0710\u072C' in verbal_prefixes:
        # Ethpaal has a doubled middle radical in the stem
        if _has_doubled_middle(stem, root_syriac):
            return 'Ethpaal'
        return 'Ethpeel'

    # ܐ alone (could be Aphel causative or 1s imperfect)
    # Only label as Aphel if the stem still contains root consonants
    # and it's not just a short imperfect form
    if '\u0710' in verbal_prefixes:
        stem_consonants = syriac_consonants_of(stem)
        root_consonants = syriac_consonants_of(root_syriac)
        if stem_consonants == root_consonants:
            return 'Aphel'

    # ܡ prefix (participle — can be any stem, but often Peal)
    # Don't label a stem for participles — they're marked [ptcp] already

    # No verbal prefix: check for Pael (doubled middle radical) or Peal
    if not verbal_prefixes:
        stem_consonants = syriac_consonants_of(stem)
        root_consonants = syriac_consonants_of(root_syriac)

        # Pael: stem has doubled middle radical (R1-R2-R2-R3)
        if _has_doubled_middle(stem, root_syriac):
            return 'Pael'

        if stem_consonants == root_consonants:
            # Check if any suffix indicates a noun/adjective (not a verb)
            nominal_suffixes = {
                '\u0718\u072C\u0710',   # ܘܬܐ abstract noun
                '\u0718\u072C\u0717',   # ܘܬܗ abstract + 3ms
                '\u072C\u0710',         # ܬܐ feminine noun
                '\u0710',               # ܐ emphatic state (noun marker)
                '\u071D\u0722',         # ܝܢ plural (noun)
            }
            # Verbal suffixes that DO indicate a verb
            verbal_suffixes = {
                '\u072C\u0718\u0722',   # ܬܘܢ 2mp
                '\u072C\u071D\u0722',   # ܬܝܢ 2fp
                '\u071D\u072C\u0717',   # ܝܬܗ 3ms obj
                '\u0722\u0722',         # ܢܢ 1cp
                '\u0722\u071D',         # ܢܝ 1s obj
                '\u072C',              # ܬ perfect
                '\u0718',              # ܘ 3mp perfect
            }
            has_nominal = any(s in nominal_suffixes for s in suffixes_removed)
            has_verbal = any(s in verbal_suffixes for s in suffixes_removed)

            # If it has nominal suffixes and no verbal ones, it's a noun
            if has_nominal and not has_verbal:
                return None
            # If it has verbal suffixes → Peal verb
            if has_verbal:
                return 'Peal'
            # Bare root with no suffixes — only label Peal if there are
            # no proclitics either (pure bare form = likely 3ms perfect)
            if not suffixes_removed and not prefixes_removed:
                return 'Peal'
            # With proclitics but no suffixes → ambiguous (noun or verb)
            return None

    return None


class WordGlosser:
    """Composes word-level glosses from root meaning + affix semantics."""

    def __init__(self, cognate_lookup, extractor, data_dir: str):
        self._cognate_lookup = cognate_lookup
        self._extractor = extractor
        self._overrides: dict = {}
        self._load_overrides(data_dir)

    def _load_overrides(self, data_dir: str) -> None:
        path = os.path.join(data_dir, 'word_glosses_override.json')
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                self._overrides = json.load(f)

    def _get_root_gloss(self, root_syriac: str, lang: str) -> str:
        """Get root-level gloss from cognates or known_roots."""
        # Try cognates first (bilingual)
        cognate = self._cognate_lookup.lookup(root_syriac)
        if cognate:
            gloss = cognate.gloss_es if lang == 'es' else cognate.gloss_en
            if gloss:
                return gloss

        # Fall back to known_roots (English only)
        gloss = self._extractor.get_root_gloss(root_syriac)
        if gloss:
            return gloss

        return ''

    def gloss(self, form: str, root_syriac: str, lang: str) -> str:
        """Return a composed gloss for a word form.

        Args:
            form: Syriac word form (e.g., ܘܕܟܬܒ)
            root_syriac: The triliteral root this form belongs to (e.g., ܟܬܒ)
            lang: 'en' or 'es'

        Returns:
            Composed gloss string, or '' if no gloss available.
        """
        # 1. Check manual overrides
        if form in self._overrides:
            return self._overrides[form].get(lang, '')

        # 2. Get root meaning
        root_gloss = self._get_root_gloss(root_syriac, lang)
        if not root_gloss:
            return ''

        # 3. Find the morphological parse that matches this root
        candidates = generate_candidate_stems(form)
        best = self._find_best_parse(candidates, root_syriac)

        if best is None:
            # No parse found — just return root gloss
            return root_gloss

        # 4. Compose: prefix glosses + root gloss + suffix glosses
        parts = []

        # Prefix glosses
        for prefix in best.prefixes_removed:
            pg = PROCLITIC_GLOSSES.get(prefix) or VERBAL_PREFIX_GLOSSES.get(prefix)
            if pg:
                parts.append(pg.get(lang, ''))

        # Root gloss
        parts.append(root_gloss)

        # Suffix glosses
        for suffix in best.suffixes_removed:
            sg = SUFFIX_GLOSSES.get(suffix)
            if sg:
                val = sg.get(lang, '')
                if val:
                    parts.append(val)

        return ''.join(parts)

    def get_stem(self, form: str, root_syriac: str) -> str | None:
        """Return the verb stem label for a word form, or None if uncertain."""
        if form in self._overrides:
            return None  # Override words are typically particles, not verbs

        candidates = generate_candidate_stems(form)
        best = self._find_best_parse(candidates, root_syriac)
        if best is None:
            return None

        return detect_verb_stem(best.prefixes_removed, best.suffixes_removed, best.stem, root_syriac)

    def _find_best_parse(self, candidates, root_syriac: str):
        """Find the StrippingResult whose stem consonants best match the root.

        Prefers exact consonant match. Among ties, prefers fewer affixes stripped.
        """
        root_consonants = syriac_consonants_of(root_syriac)
        best = None
        best_score = -1

        for candidate in candidates:
            stem_consonants = syriac_consonants_of(candidate.stem)

            if stem_consonants == root_consonants:
                # Exact match — score by simplicity (fewer affixes = better)
                affix_count = len(candidate.prefixes_removed) + len(candidate.suffixes_removed)
                score = 100 - affix_count
                if score > best_score:
                    best_score = score
                    best = candidate
            elif len(stem_consonants) >= 2 and root_consonants.startswith(stem_consonants):
                # Partial match (weak root cases) — lower priority
                score = 10
                if score > best_score:
                    best_score = score
                    best = candidate

        return best
