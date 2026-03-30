"""Hebrew & Arabic cognate lookup for Semitic triliteral roots."""

import json
import os
from dataclasses import dataclass, field

from .characters import transliterate_syriac, detect_script, strip_diacritics


@dataclass
class CognateWord:
    word: str
    transliteration: str
    meaning_es: str
    meaning_en: str
    outlier: bool = False


@dataclass
class SemanticBridge:
    outlier_key: str        # "ar:raha"
    target_root: str        # "n-w-kh" (cognates.json key)
    relationship: str       # "semantic_neighbor"
    bridge_concept_en: str
    bridge_concept_es: str


@dataclass
class GreekParallel:
    word: str              # πνεῦμα
    transliteration: str   # pneuma
    meaning_es: str
    meaning_en: str
    aramaic_range_es: str
    aramaic_range_en: str
    greek_range_es: str
    greek_range_en: str
    lost_es: str
    lost_en: str


@dataclass
class CognateEntry:
    root_syriac: str
    gloss_es: str
    gloss_en: str
    gloss_he: str = ''
    gloss_ar: str = ''
    sabor_raiz_es: str = ''
    sabor_raiz_en: str = ''
    hebrew: list[CognateWord] = field(default_factory=list)
    arabic: list[CognateWord] = field(default_factory=list)
    semantic_bridges: list[SemanticBridge] = field(default_factory=list)
    greek_parallel: GreekParallel | None = None
    paradigmatic_note_es: str = ''
    paradigmatic_note_en: str = ''
    paradigmatic_ref_override: str = ''


class CognateLookup:
    """Looks up Hebrew and Arabic cognates for a given Semitic root."""

    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        self.data_dir = data_dir
        self._cognates: dict[str, CognateEntry] = {}
        self._syriac_to_key: dict[str, str] = {}
        # Reverse indexes for cognate word lookup
        self._hebrew_word_to_keys: dict[str, list[str]] = {}
        self._hebrew_translit_to_keys: dict[str, list[str]] = {}
        self._arabic_word_to_keys: dict[str, list[str]] = {}
        self._arabic_translit_to_keys: dict[str, list[str]] = {}
        self._loaded = False

    def load(self) -> None:
        """Load the cognates dictionary from JSON."""
        if self._loaded:
            return

        cognates_path = os.path.join(self.data_dir, 'cognates.json')
        if not os.path.exists(cognates_path):
            self._loaded = True
            return

        with open(cognates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for key, entry_data in data.get('roots', {}).items():
            root_syriac = entry_data.get('root_syriac', '')

            hebrew_words = []
            for hw in entry_data.get('hebrew', []):
                hebrew_words.append(CognateWord(
                    word=hw['word'],
                    transliteration=hw['transliteration'],
                    meaning_es=hw.get('meaning_es', ''),
                    meaning_en=hw.get('meaning_en', ''),
                    outlier=hw.get('outlier', False),
                ))

            arabic_words = []
            for aw in entry_data.get('arabic', []):
                arabic_words.append(CognateWord(
                    word=aw['word'],
                    transliteration=aw['transliteration'],
                    meaning_es=aw.get('meaning_es', ''),
                    meaning_en=aw.get('meaning_en', ''),
                    outlier=aw.get('outlier', False),
                ))

            bridges = []
            for outlier_key, bridge_data in entry_data.get('semantic_bridges', {}).items():
                if bridge_data.get('target_root'):
                    bridges.append(SemanticBridge(
                        outlier_key=outlier_key,
                        target_root=bridge_data['target_root'],
                        relationship=bridge_data.get('relationship', 'semantic_neighbor'),
                        bridge_concept_en=bridge_data.get('bridge_concept_en', ''),
                        bridge_concept_es=bridge_data.get('bridge_concept_es', ''),
                    ))

            greek_parallel = None
            gp_data = entry_data.get('greek_parallel')
            if gp_data and gp_data.get('word'):
                greek_parallel = GreekParallel(
                    word=gp_data['word'],
                    transliteration=gp_data.get('transliteration', ''),
                    meaning_es=gp_data.get('meaning_es', ''),
                    meaning_en=gp_data.get('meaning_en', ''),
                    aramaic_range_es=gp_data.get('aramaic_range_es', ''),
                    aramaic_range_en=gp_data.get('aramaic_range_en', ''),
                    greek_range_es=gp_data.get('greek_range_es', ''),
                    greek_range_en=gp_data.get('greek_range_en', ''),
                    lost_es=gp_data.get('lost_es', ''),
                    lost_en=gp_data.get('lost_en', ''),
                )

            entry = CognateEntry(
                root_syriac=root_syriac,
                gloss_es=entry_data.get('gloss_es', ''),
                gloss_en=entry_data.get('gloss_en', ''),
                gloss_he=entry_data.get('gloss_he', ''),
                gloss_ar=entry_data.get('gloss_ar', ''),
                sabor_raiz_es=entry_data.get('sabor_raiz_es', ''),
                sabor_raiz_en=entry_data.get('sabor_raiz_en', ''),
                hebrew=hebrew_words,
                arabic=arabic_words,
                semantic_bridges=bridges,
                greek_parallel=greek_parallel,
                paradigmatic_note_es=entry_data.get('paradigmatic_note_es', ''),
                paradigmatic_note_en=entry_data.get('paradigmatic_note_en', ''),
                paradigmatic_ref_override=entry_data.get('paradigmatic_ref', ''),
            )

            self._cognates[key] = entry
            if root_syriac:
                self._syriac_to_key[root_syriac] = key

            # Build reverse indexes
            for hw in hebrew_words:
                hw_stripped = strip_diacritics(hw.word).strip()
                if hw_stripped:
                    self._hebrew_word_to_keys.setdefault(hw_stripped, [])
                    if key not in self._hebrew_word_to_keys[hw_stripped]:
                        self._hebrew_word_to_keys[hw_stripped].append(key)
                hw_translit = hw.transliteration.lower().strip()
                if hw_translit:
                    self._hebrew_translit_to_keys.setdefault(hw_translit, [])
                    if key not in self._hebrew_translit_to_keys[hw_translit]:
                        self._hebrew_translit_to_keys[hw_translit].append(key)

            for aw in arabic_words:
                aw_stripped = strip_diacritics(aw.word).strip()
                if aw_stripped:
                    self._arabic_word_to_keys.setdefault(aw_stripped, [])
                    if key not in self._arabic_word_to_keys[aw_stripped]:
                        self._arabic_word_to_keys[aw_stripped].append(key)
                aw_translit = aw.transliteration.lower().strip()
                if aw_translit:
                    self._arabic_translit_to_keys.setdefault(aw_translit, [])
                    if key not in self._arabic_translit_to_keys[aw_translit]:
                        self._arabic_translit_to_keys[aw_translit].append(key)

        self._loaded = True

    def lookup(self, root_syriac: str) -> CognateEntry | None:
        """Look up cognates by Syriac root string (e.g., ܟܬܒ).

        Returns CognateEntry or None if not found.
        """
        self.load()

        # Try direct Syriac lookup
        key = self._syriac_to_key.get(root_syriac)
        if key and key in self._cognates:
            return self._cognates[key]

        # Try transliterated key
        translit = transliterate_syriac(root_syriac)
        # Convert transliteration to key format: k-th-b or g-sh
        if len(root_syriac) >= 2:
            parts = []
            for ch in root_syriac:
                from .characters import SYRIAC_TO_LATIN
                if ch in SYRIAC_TO_LATIN:
                    # Normalize ' (alef) back to 'a' for JSON key lookup
                    val = SYRIAC_TO_LATIN[ch]
                    parts.append('a' if val == "'" else val)
            if len(parts) in (2, 3):
                key = '-'.join(parts)
                if key in self._cognates:
                    return self._cognates[key]

        return None

    def lookup_by_cognate_word(self, word: str) -> list[CognateEntry]:
        """Look up Syriac roots by a Hebrew or Arabic cognate word.

        Accepts:
          - Hebrew script (כתב)
          - Arabic script (كتب)
          - Latin transliteration (katav, kataba)

        Returns a list of matching CognateEntry objects.
        """
        self.load()
        word = word.strip()
        if not word:
            return []

        script = detect_script(word)
        found_keys: list[str] = []

        if script == 'hebrew':
            stripped = strip_diacritics(word)
            found_keys = self._hebrew_word_to_keys.get(stripped, [])
        elif script == 'arabic':
            stripped = strip_diacritics(word)
            found_keys = self._arabic_word_to_keys.get(stripped, [])
        else:
            # Latin transliteration — search both Hebrew and Arabic indexes
            low = word.lower()
            heb_keys = self._hebrew_translit_to_keys.get(low, [])
            ar_keys = self._arabic_translit_to_keys.get(low, [])
            seen = set()
            for k in heb_keys + ar_keys:
                if k not in seen:
                    found_keys.append(k)
                    seen.add(k)

        return [self._cognates[k] for k in found_keys if k in self._cognates]

    def has_cognates(self, root_syriac: str) -> bool:
        """Check if cognates exist for a given root."""
        return self.lookup(root_syriac) is not None

    def get_all_keys(self) -> list[str]:
        """Return all root keys (e.g., ['k-th-b', 'sh-l-m', ...])."""
        self.load()
        return list(self._cognates.keys())

    def lookup_by_key(self, key: str) -> CognateEntry | None:
        """Look up cognates by transliteration key (e.g., 'sh-l-m')."""
        self.load()
        return self._cognates.get(key)
