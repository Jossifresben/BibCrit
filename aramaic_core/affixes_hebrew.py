"""Biblical Aramaic affix stripping rules for Hebrew square script.

Biblical Aramaic uses Hebrew consonants with Aramaic morphology.
This module mirrors affixes.py but for Hebrew square script forms.
"""

from dataclasses import dataclass


@dataclass
class StrippingResult:
    stem: str
    prefixes_removed: list[str]
    suffixes_removed: list[str]


# --- Biblical Aramaic Prefixes (Hebrew script) ---
# Compound proclitics
BA_COMPOUND_PREFIXES = [
    'וב',   # w-b (and-in)
    'ול',   # w-l (and-to)
    'ומ',   # w-m (and-from)
    'לב',   # l-b (to-in)
    'למ',   # l-m (to-from)
    'וד',   # w-d (and-that, Aramaic di)
]

# Single proclitics
BA_SINGLE_PREFIXES = [
    'ו',    # w (and)
    'ד',    # d (that/of, Aramaic relative)
    'ב',    # b (in)
    'ל',    # l (to)
    'מ',    # m (from)
    'כ',    # k (like/as)
]

# Verbal prefixes (imperfect/participle)
BA_VERBAL_PREFIXES = [
    'הת',   # hit- (reflexive)
    'את',   # it- (reflexive, Aramaic)
    'אשת',  # isht- (Aramaic reflexive)
    'מת',   # mit- (participle reflexive)
    'ש',    # sh- (Shafel causative)
    'מ',    # m- (participle)
    'נ',    # n- (N-stem)
    'ת',    # t- (2nd person / 3fs)
    'י',    # y- (3ms imperfect)
    'א',    # a- (1s imperfect)
]

# --- Biblical Aramaic Suffixes (Hebrew script) ---
# Ordered longest-first for greedy matching
BA_SUFFIXES = [
    # Verbal suffixes (long)
    'תון',   # -tun (2mp)
    'תין',   # -tin (2fp)
    'נני',   # -nniy (1s energic)
    # Pronominal suffixes
    'הון',   # -hun (3mp)
    'הין',   # -hin (3fp)
    'כון',   # -kun (2mp)
    'כין',   # -kin (2fp)
    'נא',    # -na (1p, Aramaic emphatic)
    # State/number
    'יא',    # -ya (emphatic pl)
    'ין',    # -in (masc pl)
    'ון',    # -un (3mp verbal)
    'תא',    # -ta (fem/abstract)
    'תה',    # -tah (fem + 3fs)
    'ית',    # -it (fem sg perf)
    'את',    # -at (fem construct)
    # Short
    'ה',     # -h (3fs / directional)
    'י',     # -y (1s / construct)
    'ך',     # -k (2ms)
    'כ',     # -k (2ms alternate)
    'ן',     # -n (3fp / energic)
    'א',     # -a (emphatic state, very common in Aramaic)
    'ת',     # -t (1s/2ms perf / fem)
    'ו',     # -w (3mp perf)
]


def generate_candidate_stems_hebrew(word: str) -> list[StrippingResult]:
    """Generate candidate stems by stripping Biblical Aramaic affixes.

    Works on Hebrew square script words from the BA corpus.
    Returns list of StrippingResult, ordered by least stripping first.
    """
    candidates = []

    # Try compound prefix + suffix combinations
    for prefix_list in [BA_COMPOUND_PREFIXES, BA_SINGLE_PREFIXES]:
        for prefix in prefix_list:
            if word.startswith(prefix) and len(word) > len(prefix) + 1:
                after_prefix = word[len(prefix):]
                # Try each suffix
                for suffix in BA_SUFFIXES:
                    if after_prefix.endswith(suffix) and len(after_prefix) > len(suffix) + 1:
                        stem = after_prefix[:-len(suffix)]
                        if 2 <= len(stem) <= 4:
                            candidates.append(StrippingResult(
                                stem=stem,
                                prefixes_removed=[prefix],
                                suffixes_removed=[suffix]
                            ))
                # Also try without suffix
                if 2 <= len(after_prefix) <= 4:
                    candidates.append(StrippingResult(
                        stem=after_prefix,
                        prefixes_removed=[prefix],
                        suffixes_removed=[]
                    ))

    # Try verbal prefix + suffix
    for prefix in BA_VERBAL_PREFIXES:
        if word.startswith(prefix) and len(word) > len(prefix) + 1:
            after_prefix = word[len(prefix):]
            for suffix in BA_SUFFIXES:
                if after_prefix.endswith(suffix) and len(after_prefix) > len(suffix) + 1:
                    stem = after_prefix[:-len(suffix)]
                    if 2 <= len(stem) <= 4:
                        candidates.append(StrippingResult(
                            stem=stem,
                            prefixes_removed=[prefix],
                            suffixes_removed=[suffix]
                        ))
            if 2 <= len(after_prefix) <= 4:
                candidates.append(StrippingResult(
                    stem=after_prefix,
                    prefixes_removed=[prefix],
                    suffixes_removed=[]
                ))

    # Try suffix only
    for suffix in BA_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            stem = word[:-len(suffix)]
            if 2 <= len(stem) <= 4:
                candidates.append(StrippingResult(
                    stem=stem,
                    prefixes_removed=[],
                    suffixes_removed=[suffix]
                ))

    # The word itself (no stripping)
    if 2 <= len(word) <= 4:
        candidates.append(StrippingResult(
            stem=word,
            prefixes_removed=[],
            suffixes_removed=[]
        ))

    return candidates
