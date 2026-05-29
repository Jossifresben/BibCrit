"""
ref_utils.py — BibCrit reference-string utilities

Shared helpers for parsing and validating biblical reference strings.
"""

import re

# em-dash, en-dash, or hyphen
_DASH = r'[-\u2013\u2014]'


def estimate_verse_count(ref: str) -> int:
    """Return a rough upper-bound estimate of verses in a reference string.

    Handles the common input patterns:
      - "Amos 5:1-17"         → same-chapter range   → 17-1+1 = 17
      - "Genesis 6:1-9:17"   → cross-chapter range  → (9-6+1)×30 = 120
      - "Genesis 6-9"         → chapter range        → (9-6+1)×30 = 120
      - "Genesis 5"           → single chapter       → 20 (safe default)
      - "Isaiah 7:14"         → single verse         → 20 (safe default)

    NOTE: same-chapter verse range must be checked BEFORE chapter range to
    avoid "5:1-17" being misread as chapter range "1→17".

    Returns a deliberately generous estimate so the guard fires early on
    genuinely long passages, not just at the exact limit.
    """
    if not ref:
        return 0

    # 1. Same-chapter verse range: ":1-17"  — MUST come first
    m = re.search(r':\s*(\d+)\s*' + _DASH + r'\s*(\d+)\s*$', ref)
    if m:
        return int(m.group(2)) - int(m.group(1)) + 1

    # 2. Cross-chapter range: "6:1 - 9:17"
    m = re.search(r'(\d+)\s*:\s*\d+\s*' + _DASH + r'\s*(\d+)\s*:', ref)
    if m:
        chaps = int(m.group(2)) - int(m.group(1)) + 1
        return chaps * 30

    # 3. Chapter range: "6-9" (no colons anywhere in the range part)
    m = re.search(r'\b(\d+)\s*' + _DASH + r'\s*(\d+)\b(?!\s*:)', ref)
    if m:
        d = int(m.group(2)) - int(m.group(1))
        if 0 < d < 50:
            return (d + 1) * 30

    # 4. Single chapter or verse — safe
    return 20


# Per-tool hard limits (verses).
# Set by output density, not just timeout risk:
#   verbose (word-level / citation-per-verse): 25–35
#   structural (chiasm, source, numerical):    50–60
# Scribal and genealogy operate on whole books — no limit applied.
TOOL_VERSE_LIMITS: dict[str, int] = {
    'backtranslation':  25,   # retroversion: ~50 tokens/word, extremely dense
    'nt_ot':            25,   # citation form + scholarly note per allusion
    'patristic':        25,   # full Father-by-Father citations per passage
    'divergence':       30,   # word-level table for every MT/LXX difference
    'theological':      30,   # flag + motivation analysis per revision
    'dss':              35,   # 5-tradition comparison, moderate density
    'targum':           35,   # 3-tradition comparison with word-level analysis
    'nt_text':          30,   # Manuscript family analysis with variant register
    'lxx_ms_variants':  30,   # LXX uncial divergences (B/Aleph/A) per passage
    'stl':              50,   # STL Bridge — canonical context; up to one chapter
    'chiasm':           50,   # structural overview, lower output per verse
    'numerical':        50,   # chapter-level anyway
    'source':           60,   # Genesis 1:1-2:25 = 56 verses — keep just under
}


# Books covered by Targum Onkelos (Torah)
_TARGUM_TORAH = {
    'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
}

# Books covered by Targum Jonathan (Former + Latter Prophets)
_TARGUM_PROPHETS = {
    'joshua', 'judges', '1 samuel', '2 samuel', '1 kings', '2 kings',
    'isaiah', 'jeremiah', 'ezekiel',
    'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah',
    'nahum', 'habakkuk', 'zephaniah', 'haggai', 'zechariah', 'malachi',
}

_TARGUM_ALL = _TARGUM_TORAH | _TARGUM_PROPHETS


def validate_targum_reference(reference: str) -> str | None:
    """Return error string if reference is outside Targum coverage, else None.

    Targum covers Torah (Onkelos) and Prophets (Jonathan) only.
    Writings (Psalms, Proverbs, Job, etc.) have no Targum in this corpus.
    """
    parts = reference.strip().lower().split()
    if not parts:
        return 'Please enter a reference.'
    # Handle multi-word book names: "1 samuel", "2 kings", etc.
    if parts[0].isdigit() and len(parts) >= 2:
        book = parts[0] + ' ' + parts[1].split(':')[0]
    else:
        book = parts[0].split(':')[0]
    book = book.strip()

    if book in _TARGUM_ALL:
        return None

    return (
        f'"{reference}" is in the Writings — Targum coverage is limited to Torah (Onkelos) '
        f'and Prophets (Jonathan). For Psalms, Proverbs, Job, or other Writings, '
        f'use the Ancient Witness Bridge or Theological Revision Detector instead.'
    )


# NT books (Matthew–Revelation, 27 books)
_NT_BOOKS = {
    'matthew', 'mark', 'luke', 'john', 'acts', 'romans',
    '1 corinthians', '2 corinthians', 'galatians', 'ephesians',
    'philippians', 'colossians', '1 thessalonians', '2 thessalonians',
    '1 timothy', '2 timothy', 'titus', 'philemon', 'hebrews',
    'james', '1 peter', '2 peter', '1 john', '2 john', '3 john',
    'jude', 'revelation',
}


def validate_nt_reference(reference: str) -> str | None:
    """Return error string if reference is outside the NT canon, else None.

    The NT Text Analyzer is for Matthew–Revelation only.
    For OT manuscript comparison use the Ancient Witness Bridge.
    """
    parts = reference.strip().lower().split()
    if not parts:
        return 'Please enter a reference.'
    if parts[0].isdigit() and len(parts) >= 2:
        book = parts[0] + ' ' + parts[1].split(':')[0]
    else:
        book = parts[0].split(':')[0]

    if book in _NT_BOOKS:
        return None

    return (
        f'"{reference}" appears to be an Old Testament reference. '
        'The NT Textual Tradition Analyzer covers Matthew–Revelation only. '
        'For OT manuscript comparison, use the Ancient Witness Bridge (/dss).'
    )
