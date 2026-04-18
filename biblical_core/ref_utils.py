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
    'chiasm':           50,   # structural overview, lower output per verse
    'numerical':        50,   # chapter-level anyway
    'source':           60,   # Genesis 1:1-2:25 = 56 verses — keep just under
}
