"""Core root extraction engine for Syriac and Biblical Aramaic triliteral roots."""

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field

from .characters import (
    SYRIAC_CONSONANTS, WEAK_LETTERS, syriac_consonants_of, transliterate_syriac,
    HEBREW_CONSONANTS, HEBREW_WEAK, hebrew_consonants_of, hebrew_to_syriac,
    transliterate_hebrew, detect_script, normalize_root_to_latin,
)
from .corpus import AramaicCorpus
from .affixes import generate_candidate_stems
from .affixes_hebrew import generate_candidate_stems_hebrew
from .glosser import detect_verb_stem


@dataclass
class RootMatch:
    """A word form matched to a root, with its verse references."""
    form: str
    transliteration: str
    references: list[str] = field(default_factory=list)
    count: int = 0


@dataclass
class RootEntry:
    """All information about a root found in the corpus."""
    root: str
    root_transliteration: str
    matches: list[RootMatch] = field(default_factory=list)
    total_occurrences: int = 0
    corpus_counts: dict[str, int] = field(default_factory=dict)


class RootExtractor:
    """Extracts triliteral roots from Syriac words and builds a root index."""

    def __init__(self, corpus: AramaicCorpus, data_dir: str | None = None):
        self.corpus = corpus
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.data_dir = data_dir

        # Known roots: root_string -> {gloss, forms}
        self._known_roots: dict = {}
        # Form -> root mapping (built from known_roots forms lists)
        self._form_to_root: dict[str, str] = {}
        # Stopwords set
        self._stopwords: set[str] = set()
        # Pre-computed root index: root -> RootEntry
        self._root_index: dict[str, RootEntry] = {}
        # Word -> root mapping (built during build_index)
        self._word_to_root: dict[str, str] = {}
        # Word -> confidence score (built during build_index)
        self._word_to_score: dict[str, float] = {}
        # Word -> verb stem label (built during build_index)
        self._word_to_stem: dict[str, str | None] = {}
        self._built = False

    def load_data(self) -> None:
        """Load known roots and stopwords from JSON files."""
        # Load known roots
        roots_path = os.path.join(self.data_dir, 'known_roots.json')
        if os.path.exists(roots_path):
            with open(roots_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._known_roots = data.get('roots', {})
            # Build form -> root reverse mapping
            for root_str, info in self._known_roots.items():
                root_clean = root_str.strip()
                for form in info.get('forms', []):
                    self._form_to_root[form] = root_clean

        # Load stopwords
        stop_path = os.path.join(self.data_dir, 'stopwords.json')
        if os.path.exists(stop_path):
            with open(stop_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for category in data.values():
                if isinstance(category, list):
                    self._stopwords.update(category)

    def _is_stopword(self, word: str) -> bool:
        return word in self._stopwords

    def _get_word_stem(self, word: str, root_syriac: str) -> str | None:
        """Return the verb stem label for a Syriac word form, or None."""
        script = detect_script(word)
        if script != 'syriac':
            return None
        candidates = generate_candidate_stems(word)
        # Find the candidate whose stem consonants best match the root
        root_consonants = syriac_consonants_of(root_syriac)
        best = None
        best_score = -1
        for candidate in candidates:
            stem_consonants = syriac_consonants_of(candidate.stem)
            if stem_consonants == root_consonants:
                # Exact match — prefer fewer affixes stripped
                score = 10 - len(candidate.prefixes_removed) - len(candidate.suffixes_removed)
                if score > best_score:
                    best_score = score
                    best = candidate
        if best is None:
            return None
        return detect_verb_stem(best.prefixes_removed, best.suffixes_removed, best.stem, root_syriac)

    def _extract_root_for_word(self, word: str) -> str | None:
        """Try to extract a root from a single word.

        Handles both Syriac script and Hebrew square script (Biblical Aramaic).
        Returns the root as a 2- or 3-character string in the word's native script, or None.
        """
        result = self._extract_root_with_score(word)
        return result[0] if result else None

    def _extract_root_with_score(self, word: str) -> tuple[str, float] | None:
        """Extract a root and its confidence score from a single word.

        Returns (root, score) where score is 0.0-1.0, or None if no root found.
        Score tiers: High (>=0.8), Medium (0.5-0.8), Low (<0.5).
        """
        script = detect_script(word)

        if script == 'hebrew':
            root = self._extract_root_hebrew(word)
            if root is None:
                return None
            # Estimate score for Hebrew path
            syriac_equiv = hebrew_to_syriac(root)
            if syriac_equiv in self._known_roots:
                return (root, 0.9)
            return (root, 0.5)

        # --- Syriac script path (original logic) ---
        # 1. Direct form lookup in known dictionary
        if word in self._form_to_root:
            return (self._form_to_root[word], 1.0)

        # 2. Get consonants only
        consonants = syriac_consonants_of(word)
        if not consonants:
            return None

        # 3. If exactly 3 consonants, it might be a bare root
        if len(consonants) == 3:
            if consonants in self._known_roots:
                return (consonants, 0.95)
            return (consonants, 0.5)

        # 3b. If exactly 2 consonants and it's a known biliteral root
        if len(consonants) == 2 and consonants in self._known_roots:
            return (consonants, 0.85)

        # 4. Generate candidate stems via affix stripping
        candidates = generate_candidate_stems(word)

        best_root = None
        best_score = -1

        for candidate in candidates:
            stem = candidate.stem
            stem_consonants = syriac_consonants_of(stem)

            if len(stem_consonants) == 3:
                root_candidate = stem_consonants
                score = self._score_root(root_candidate, candidate)
                if score > best_score:
                    best_score = score
                    best_root = root_candidate

            elif len(stem_consonants) == 4:
                for i in range(1, 3):
                    if i < len(stem_consonants) and stem_consonants[i] in WEAK_LETTERS:
                        reduced = stem_consonants[:i] + stem_consonants[i+1:]
                        if len(reduced) == 3:
                            score = self._score_root(reduced, candidate) * 0.8
                            if score > best_score:
                                best_score = score
                                best_root = reduced

            elif len(stem_consonants) == 2:
                for weak in ['\u0718', '\u071D', '\u0710']:  # ܘ ܝ ܐ
                    reconstructed = stem_consonants[0] + weak + stem_consonants[1]
                    score = self._score_root(reconstructed, candidate) * 0.6
                    if score > best_score:
                        best_score = score
                        best_root = reconstructed

        if best_root is not None:
            return (best_root, best_score)
        return None

    def _extract_root_hebrew(self, word: str) -> str | None:
        """Extract root from a Biblical Aramaic word in Hebrew square script.

        Returns root in Hebrew script (e.g., כתב not ܟܬܒ).
        The build_index method normalizes to a shared key via latin transliteration.
        """
        # Check if the Syriac equivalent is a known form
        syriac_equiv = hebrew_to_syriac(word)
        if syriac_equiv in self._form_to_root:
            syriac_root = self._form_to_root[syriac_equiv]
            # Return root in Hebrew script for display
            return word  # will be normalized later

        consonants = hebrew_consonants_of(word)
        if not consonants:
            return None

        # 3 consonants = likely root
        if len(consonants) == 3:
            return consonants

        # 2 consonants and known (check Syriac equivalent)
        if len(consonants) == 2:
            syriac_cons = hebrew_to_syriac(consonants)
            if syriac_cons in self._known_roots:
                return consonants

        # Affix stripping for Hebrew script
        candidates = generate_candidate_stems_hebrew(word)

        best_root = None
        best_score = -1

        for candidate in candidates:
            stem = candidate.stem
            stem_consonants = hebrew_consonants_of(stem)

            if len(stem_consonants) == 3:
                # Check if Syriac equivalent is known
                syriac_equiv = hebrew_to_syriac(stem_consonants)
                score = 0.5
                if syriac_equiv in self._known_roots:
                    score += 0.4
                if not candidate.prefixes_removed and not candidate.suffixes_removed:
                    score += 0.1
                if score > best_score:
                    best_score = score
                    best_root = stem_consonants

            elif len(stem_consonants) == 4:
                # Try removing weak letters (ו י א ה)
                for i in range(1, 3):
                    if i < len(stem_consonants) and stem_consonants[i] in HEBREW_WEAK:
                        reduced = stem_consonants[:i] + stem_consonants[i+1:]
                        if len(reduced) == 3:
                            syriac_equiv = hebrew_to_syriac(reduced)
                            score = 0.5
                            if syriac_equiv in self._known_roots:
                                score += 0.3
                            score *= 0.8
                            if score > best_score:
                                best_score = score
                                best_root = reduced

            elif len(stem_consonants) == 2:
                for weak in ['\u05D5', '\u05D9', '\u05D0']:  # ו י א
                    reconstructed = stem_consonants[0] + weak + stem_consonants[1]
                    syriac_equiv = hebrew_to_syriac(reconstructed)
                    score = 0.5
                    if syriac_equiv in self._known_roots:
                        score += 0.3
                    score *= 0.6
                    if score > best_score:
                        best_score = score
                        best_root = reconstructed

        return best_root

    def _score_root(self, root: str, candidate=None) -> float:
        """Score a root candidate. Higher = more likely correct."""
        score = 0.5  # base score

        # Known root bonus
        if root in self._known_roots:
            score += 0.4

        # Minimal stripping bonus
        if candidate and not candidate.prefixes_removed and not candidate.suffixes_removed:
            score += 0.1

        return score

    def build_index(self) -> None:
        """Process the entire corpus and build the root index.

        Handles both Syriac and Hebrew script words. Hebrew script roots
        are normalized to their Syriac equivalents so that cross-corpus
        root searches work (e.g., כתב and ܟܬܒ resolve to the same root).
        """
        if self._built:
            return

        self.load_data()
        self.corpus.load()

        # Collect roots per canonical key (Syriac script)
        # canonical_root -> { form -> [refs] }
        root_data: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        # Track which scripts a root appears in
        self._root_scripts: dict[str, set[str]] = defaultdict(set)
        # Track original-script roots for display
        self._root_display: dict[str, dict[str, str]] = defaultdict(dict)

        for word in self.corpus.get_unique_words():
            if self._is_stopword(word):
                continue
            if '-' in word:
                continue

            result = self._extract_root_with_score(word)
            if result is None:
                continue
            root, score = result

            word_script = detect_script(word)

            # Normalize Hebrew roots to Syriac for a canonical key
            if word_script == 'hebrew':
                canonical_root = hebrew_to_syriac(root)
                self._root_scripts[canonical_root].add('hebrew')
                self._root_display[canonical_root]['hebrew'] = root
            else:
                canonical_root = root
                self._root_scripts[canonical_root].add('syriac')
                self._root_display[canonical_root]['syriac'] = root

            self._word_to_root[word] = canonical_root
            self._word_to_score[word] = score
            self._word_to_stem[word] = self._get_word_stem(word, canonical_root)

            refs = self.corpus.get_occurrences(word)
            root_data[canonical_root][word] = refs

        # Build RootEntry objects
        for root_str, forms_dict in root_data.items():
            entry = RootEntry(
                root=root_str,
                root_transliteration=transliterate_syriac(root_str),
            )
            for form, refs in forms_dict.items():
                form_script = detect_script(form)
                if form_script == 'hebrew':
                    translit = transliterate_hebrew(form)
                else:
                    translit = transliterate_syriac(form)

                match = RootMatch(
                    form=form,
                    transliteration=translit,
                    references=refs,
                    count=len(refs),
                )
                entry.matches.append(match)
                entry.total_occurrences += len(refs)
                for ref in refs:
                    cid = self.corpus.get_verse_corpus(ref)
                    if cid:
                        entry.corpus_counts[cid] = entry.corpus_counts.get(cid, 0) + 1

            entry.matches.sort(key=lambda m: m.count, reverse=True)
            self._root_index[root_str] = entry

        self._built = True

    def get_root_scripts(self, root_syriac: str) -> set[str]:
        """Return the set of scripts this root appears in ('syriac', 'hebrew')."""
        self.build_index()
        return self._root_scripts.get(root_syriac, set())

    def get_root_display(self, root_syriac: str) -> dict[str, str]:
        """Return display forms of the root in each script it appears in.
        E.g., {'syriac': 'ܟܬܒ', 'hebrew': 'כתב'}"""
        self.build_index()
        return self._root_display.get(root_syriac, {})

    def lookup_root(self, root_syriac: str) -> RootEntry | None:
        """Look up a root in the pre-built index.

        Args:
            root_syriac: 3-character Syriac root string (e.g., ܟܬܒ)

        Returns:
            RootEntry with all matched forms and references, or None.
        """
        self.build_index()
        return self._root_index.get(root_syriac)

    def get_all_roots(self) -> list[RootEntry]:
        """Return all roots found in the corpus, sorted by frequency."""
        self.build_index()
        roots = list(self._root_index.values())
        roots.sort(key=lambda r: r.total_occurrences, reverse=True)
        return roots

    def get_root_count(self) -> int:
        """Return the number of unique roots found."""
        self.build_index()
        return len(self._root_index)

    def lookup_word_root(self, word: str) -> str | None:
        """Return the Syriac root for a given word form, or None."""
        self.build_index()
        return self._word_to_root.get(word)

    def lookup_word_confidence(self, word: str) -> float | None:
        """Return the confidence score (0.0-1.0) for a word's root extraction.

        Tiers: High (>=0.8), Medium (0.5-0.8), Low (<0.5).
        Returns None if the word has no root.
        """
        self.build_index()
        return self._word_to_score.get(word)

    def lookup_word_root_with_confidence(self, word: str) -> tuple[str, float] | None:
        """Return (root, confidence) for a word, or None."""
        self.build_index()
        root = self._word_to_root.get(word)
        if root is None:
            return None
        score = self._word_to_score.get(word, 0.5)
        return (root, score)

    def lookup_word_stem(self, word: str) -> str | None:
        """Return the verb stem label for a word (e.g., 'Peal', 'Ethpeel'), or None."""
        self.build_index()
        return self._word_to_stem.get(word)

    def get_root_gloss(self, root_syriac: str) -> str:
        """Return the English gloss for a root from known_roots.json."""
        self.load_data()
        info = self._known_roots.get(root_syriac)
        if info:
            return info.get('gloss', '')
        return ''
