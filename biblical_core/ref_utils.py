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


# Per-tool hard limits (verses)
TOOL_VERSE_LIMITS: dict[str, int] = {
    'divergence':     50,
    'backtranslation': 40,
    'dss':            50,
    'numerical':      50,
    'theological':    50,
    'patristic':      50,
    'nt_ot':          40,
    'chiasm':         65,
    'source':         65,
    # 'scribal' and 'genealogy' operate on whole books — no limit applied
}
