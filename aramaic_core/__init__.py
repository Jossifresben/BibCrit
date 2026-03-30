"""Aramaic Core — shared linguistic engine for Aramaic text analysis.

Provides triliteral root extraction, cognate lookup, morphological analysis,
and transliteration across Syriac, Hebrew, and Arabic scripts.
"""

from .characters import (
    SYRIAC_CONSONANTS, WEAK_LETTERS, PROCLITIC_LETTERS,
    SYRIAC_TO_LATIN, LATIN_TO_SYRIAC,
    HEBREW_TO_LATIN, ARABIC_TO_LATIN,
    SYRIAC_TO_ACADEMIC, SYRIAC_TO_HEBREW, SYRIAC_TO_ARABIC,
    transliterate_syriac, transliterate_hebrew, transliterate_arabic,
    transliterate_syriac_academic, transliterate_syriac_to_hebrew,
    transliterate_syriac_to_arabic,
    parse_root_input, syriac_consonants_of, detect_script, strip_diacritics,
    semitic_root_variants,
)
from .corpus import AramaicCorpus
from .extractor import RootExtractor, RootEntry, RootMatch
from .cognates import CognateLookup, CognateEntry
from .glosser import WordGlosser

__version__ = '0.1.0'
