"""Syriac, Hebrew, and Arabic character constants and transliteration maps."""

# --- Syriac Consonants (Estrangela/Eastern) ---
# 22 letters, Unicode range U+0710-U+072C

SYRIAC_CONSONANTS = frozenset([
    '\u0710',  # ܐ Alaph
    '\u0712',  # ܒ Beth
    '\u0713',  # ܓ Gamal
    '\u0715',  # ܕ Dalath
    '\u0717',  # ܗ He
    '\u0718',  # ܘ Waw
    '\u0719',  # ܙ Zain
    '\u071A',  # ܚ Heth
    '\u071B',  # ܛ Teth
    '\u071D',  # ܝ Yudh
    '\u071F',  # ܟ Kaph
    '\u0720',  # ܠ Lamadh
    '\u0721',  # ܡ Mim
    '\u0722',  # ܢ Nun
    '\u0723',  # ܣ Semkath
    '\u0725',  # ܥ E (Ayin)
    '\u0726',  # ܦ Pe
    '\u0728',  # ܨ Sadhe
    '\u0729',  # ܩ Qaph
    '\u072A',  # ܪ Rish
    '\u072B',  # ܫ Shin
    '\u072C',  # ܬ Taw
])

# Weak letters (matres lectionis) - can be root consonants or vowel markers
WEAK_LETTERS = frozenset(['\u0710', '\u0718', '\u071D'])  # ܐ ܘ ܝ

# Proclitic letters - single-letter particles that attach to words
PROCLITIC_LETTERS = frozenset(['\u0715', '\u0718', '\u0712', '\u0720'])  # ܕ ܘ ܒ ܠ

# --- Syriac -> Latin transliteration ---
SYRIAC_TO_LATIN = {
    '\u0710': "'",    # ܐ Alaph (glottal stop)
    '\u0712': 'b',    # ܒ Beth
    '\u0713': 'g',    # ܓ Gamal
    '\u0715': 'd',    # ܕ Dalath
    '\u0717': 'h',    # ܗ He
    '\u0718': 'w',    # ܘ Waw
    '\u0719': 'z',    # ܙ Zain
    '\u071A': 'kh',   # ܚ Heth
    '\u071B': 'T',    # ܛ Teth (capital to distinguish from ܬ)
    '\u071D': 'y',    # ܝ Yudh
    '\u071F': 'k',    # ܟ Kaph
    '\u0720': 'l',    # ܠ Lamadh
    '\u0721': 'm',    # ܡ Mim
    '\u0722': 'n',    # ܢ Nun
    '\u0723': 's',    # ܣ Semkath
    '\u0725': 'e',    # ܥ E (Ayin)
    '\u0726': 'p',    # ܦ Pe
    '\u0728': 'ts',   # ܨ Sadhe
    '\u0729': 'q',    # ܩ Qaph
    '\u072A': 'r',    # ܪ Rish
    '\u072B': 'sh',   # ܫ Shin
    '\u072C': 'th',   # ܬ Taw
}

# --- Latin -> Syriac (reverse map for user input parsing) ---
# Handles both upper and lower case input
LATIN_TO_SYRIAC = {
    "'":  '\u0710',  # ܐ Alaph (glottal stop)
    'a':  '\u0710',  # ܐ (alternate input for backward compatibility)
    'b':  '\u0712',  # ܒ
    'g':  '\u0713',  # ܓ
    'd':  '\u0715',  # ܕ
    'h':  '\u0717',  # ܗ
    'w':  '\u0718',  # ܘ
    'z':  '\u0719',  # ܙ
    'kh': '\u071A',  # ܚ
    'T':  '\u071B',  # ܛ
    'y':  '\u071D',  # ܝ
    'k':  '\u071F',  # ܟ
    'l':  '\u0720',  # ܠ
    'm':  '\u0721',  # ܡ
    'n':  '\u0722',  # ܢ
    's':  '\u0723',  # ܣ
    'e':  '\u0725',  # ܥ E (Ayin)
    'o':  '\u0725',  # ܥ (alternate input for Hebrew-familiar users)
    'p':  '\u0726',  # ܦ
    'ts': '\u0728',  # ܨ
    'q':  '\u0729',  # ܩ
    'r':  '\u072A',  # ܪ
    'sh': '\u072B',  # ܫ
    'th': '\u072C',  # ܬ
}

# --- Hebrew consonant transliteration (for display) ---
HEBREW_TO_LATIN = {
    '\u05D0': 'a',    # א Alef
    '\u05D1': 'b',    # ב Bet
    '\u05D2': 'g',    # ג Gimel
    '\u05D3': 'd',    # ד Dalet
    '\u05D4': 'h',    # ה He
    '\u05D5': 'w',    # ו Vav
    '\u05D6': 'z',    # ז Zayin
    '\u05D7': 'kh',   # ח Het
    '\u05D8': 'T',    # ט Tet
    '\u05D9': 'y',    # י Yod
    '\u05DA': 'k',    # ך Kaf final
    '\u05DB': 'k',    # כ Kaf
    '\u05DC': 'l',    # ל Lamed
    '\u05DD': 'm',    # ם Mem final
    '\u05DE': 'm',    # מ Mem
    '\u05DF': 'n',    # ן Nun final
    '\u05E0': 'n',    # נ Nun
    '\u05E1': 's',    # ס Samekh
    '\u05E2': 'e',    # ע Ayin
    '\u05E3': 'p',    # ף Pe final
    '\u05E4': 'p',    # פ Pe
    '\u05E5': 'ts',   # ץ Tsadi final
    '\u05E6': 'ts',   # צ Tsadi
    '\u05E7': 'q',    # ק Qof
    '\u05E8': 'r',    # ר Resh
    '\u05E9': 'sh',   # ש Shin
    '\u05EA': 'th',   # ת Tav
}

# --- Arabic consonant transliteration (for display) ---
ARABIC_TO_LATIN = {
    '\u0627': 'a',    # ا Alif
    '\u0628': 'b',    # ب Ba
    '\u062A': 't',    # ت Ta
    '\u062B': 'th',   # ث Tha
    '\u062C': 'j',    # ج Jim
    '\u062D': 'H',    # ح Ha
    '\u062E': 'kh',   # خ Kha
    '\u062F': 'd',    # د Dal
    '\u0630': 'dh',   # ذ Dhal
    '\u0631': 'r',    # ر Ra
    '\u0632': 'z',    # ز Zay
    '\u0633': 's',    # س Sin
    '\u0634': 'sh',   # ش Shin
    '\u0635': 'S',    # ص Sad
    '\u0636': 'D',    # ض Dad
    '\u0637': 'T',    # ط Ta
    '\u0638': 'Z',    # ظ Za
    '\u0639': 'e',    # ع Ayn
    '\u063A': 'gh',   # غ Ghayn
    '\u0641': 'f',    # ف Fa
    '\u0642': 'q',    # ق Qaf
    '\u0643': 'k',    # ك Kaf
    '\u0644': 'l',    # ل Lam
    '\u0645': 'm',    # م Mim
    '\u0646': 'n',    # ن Nun
    '\u0647': 'h',    # ه Ha
    '\u0648': 'w',    # و Waw
    '\u064A': 'y',    # ي Ya
}


# --- Syriac -> Academic transliteration (scholarly standard) ---
SYRIAC_TO_ACADEMIC = {
    '\u0710': 'ʾ',    # ܐ Alaph
    '\u0712': 'b',    # ܒ Beth
    '\u0713': 'g',    # ܓ Gamal
    '\u0715': 'd',    # ܕ Dalath
    '\u0717': 'h',    # ܗ He
    '\u0718': 'w',    # ܘ Waw
    '\u0719': 'z',    # ܙ Zain
    '\u071A': 'ḥ',    # ܚ Heth
    '\u071B': 'ṭ',    # ܛ Teth
    '\u071D': 'y',    # ܝ Yudh
    '\u071F': 'k',    # ܟ Kaph
    '\u0720': 'l',    # ܠ Lamadh
    '\u0721': 'm',    # ܡ Mim
    '\u0722': 'n',    # ܢ Nun
    '\u0723': 's',    # ܣ Semkath
    '\u0725': 'ʿ',    # ܥ Ayin
    '\u0726': 'p',    # ܦ Pe
    '\u0728': 'ṣ',    # ܨ Sadhe
    '\u0729': 'q',    # ܩ Qaph
    '\u072A': 'r',    # ܪ Rish
    '\u072B': 'š',    # ܫ Shin
    '\u072C': 't',    # ܬ Taw
}


# --- Syriac -> Hebrew script ---
SYRIAC_TO_HEBREW = {
    '\u0710': '\u05D0',  # ܐ -> א Alef
    '\u0712': '\u05D1',  # ܒ -> ב Bet
    '\u0713': '\u05D2',  # ܓ -> ג Gimel
    '\u0715': '\u05D3',  # ܕ -> ד Dalet
    '\u0717': '\u05D4',  # ܗ -> ה He
    '\u0718': '\u05D5',  # ܘ -> ו Vav
    '\u0719': '\u05D6',  # ܙ -> ז Zayin
    '\u071A': '\u05D7',  # ܚ -> ח Het
    '\u071B': '\u05D8',  # ܛ -> ט Tet
    '\u071D': '\u05D9',  # ܝ -> י Yod
    '\u071F': '\u05DB',  # ܟ -> כ Kaf
    '\u0720': '\u05DC',  # ܠ -> ל Lamed
    '\u0721': '\u05DE',  # ܡ -> מ Mem
    '\u0722': '\u05E0',  # ܢ -> נ Nun
    '\u0723': '\u05E1',  # ܣ -> ס Samekh
    '\u0725': '\u05E2',  # ܥ -> ע Ayin
    '\u0726': '\u05E4',  # ܦ -> פ Pe
    '\u0728': '\u05E6',  # ܨ -> צ Tsadi
    '\u0729': '\u05E7',  # ܩ -> ק Qof
    '\u072A': '\u05E8',  # ܪ -> ר Resh
    '\u072B': '\u05E9',  # ܫ -> ש Shin
    '\u072C': '\u05EA',  # ܬ -> ת Tav
}

# --- Syriac -> Arabic script ---
SYRIAC_TO_ARABIC = {
    '\u0710': '\u0627',  # ܐ -> ا Alif
    '\u0712': '\u0628',  # ܒ -> ب Ba
    '\u0713': '\u062C',  # ܓ -> ج Jim
    '\u0715': '\u062F',  # ܕ -> د Dal
    '\u0717': '\u0647',  # ܗ -> ه Ha
    '\u0718': '\u0648',  # ܘ -> و Waw
    '\u0719': '\u0632',  # ܙ -> ز Zay
    '\u071A': '\u062D',  # ܚ -> ح Ha
    '\u071B': '\u0637',  # ܛ -> ط Ta
    '\u071D': '\u064A',  # ܝ -> ي Ya
    '\u071F': '\u0643',  # ܟ -> ك Kaf
    '\u0720': '\u0644',  # ܠ -> ل Lam
    '\u0721': '\u0645',  # ܡ -> م Mim
    '\u0722': '\u0646',  # ܢ -> ن Nun
    '\u0723': '\u0633',  # ܣ -> س Sin
    '\u0725': '\u0639',  # ܥ -> ع Ayn
    '\u0726': '\u0641',  # ܦ -> ف Fa
    '\u0728': '\u0635',  # ܨ -> ص Sad
    '\u0729': '\u0642',  # ܩ -> ق Qaf
    '\u072A': '\u0631',  # ܪ -> ر Ra
    '\u072B': '\u0634',  # ܫ -> ش Shin
    '\u072C': '\u062A',  # ܬ -> ت Ta
}


def transliterate_syriac_to_hebrew(text: str) -> str:
    """Convert Syriac Unicode text to Hebrew script."""
    result = []
    for ch in text:
        if ch in SYRIAC_TO_HEBREW:
            result.append(SYRIAC_TO_HEBREW[ch])
        elif ch == ' ':
            result.append(' ')
        elif ch == '-':
            result.append('-')
    return ''.join(result)


def transliterate_syriac_to_arabic(text: str) -> str:
    """Convert Syriac Unicode text to Arabic script."""
    result = []
    for ch in text:
        if ch in SYRIAC_TO_ARABIC:
            result.append(SYRIAC_TO_ARABIC[ch])
        elif ch == ' ':
            result.append(' ')
        elif ch == '-':
            result.append('-')
    return ''.join(result)


def transliterate_syriac_academic(text: str) -> str:
    """Convert Syriac Unicode text to academic/scholarly transliteration."""
    result = []
    for ch in text:
        if ch in SYRIAC_TO_ACADEMIC:
            result.append(SYRIAC_TO_ACADEMIC[ch])
        elif ch == ' ':
            result.append(' ')
        elif ch == '-':
            result.append('-')
    return ''.join(result)


def transliterate_syriac(text: str) -> str:
    """Convert Syriac Unicode text to simple Latin transliteration."""
    result = []
    for ch in text:
        if ch in SYRIAC_TO_LATIN:
            result.append(SYRIAC_TO_LATIN[ch])
        elif ch == ' ':
            result.append(' ')
        elif ch == '-':
            result.append('-')
    return ''.join(result)


def transliterate_hebrew(text: str) -> str:
    """Convert Hebrew Unicode text to simple Latin transliteration."""
    result = []
    for ch in text:
        if ch in HEBREW_TO_LATIN:
            result.append(HEBREW_TO_LATIN[ch])
        elif ch == ' ':
            result.append(' ')
    return ''.join(result)


def transliterate_arabic(text: str) -> str:
    """Convert Arabic Unicode text to simple Latin transliteration."""
    result = []
    for ch in text:
        if ch in ARABIC_TO_LATIN:
            result.append(ARABIC_TO_LATIN[ch])
        elif ch == ' ':
            result.append(' ')
    return ''.join(result)


def translit_word_to_syriac(text: str) -> str | None:
    """Convert a Latin-script transliteration of a Syriac word to Syriac Unicode.

    Accepts:
    - Dash-separated consonants: 'sh-l-m', 'k-t-b', 'w-sh-l-m'
    - Continuous consonant string: 'shlem', 'ktb', 'wshlem'

    Uses greedy left-to-right matching, preferring digraphs (sh, kh, th, ts).
    Adds 't' as a fallback mapping to ܬ Taw (common shorthand for 'th').

    Returns the Syriac Unicode string, or None if any part cannot be mapped.
    """
    text = text.strip()
    if not text:
        return None

    lower = text.lower()

    # Extended map shared by both paths: adds 't' → ܬ Taw as a fallback
    # so users can write 'k-t-b' or 'ktb' instead of requiring 'k-th-b'.
    extended = dict(LATIN_TO_SYRIAC)
    extended.setdefault('t', '\u072C')   # ܬ Taw

    # Dash- or space-separated: each segment is one consonant label
    if '-' in lower or (' ' in lower and len(lower.split()) > 1):
        sep = '-' if '-' in lower else ' '
        parts = [p.strip() for p in lower.split(sep) if p.strip()]
        result = []
        for part in parts:
            if part in extended:
                result.append(extended[part])
            else:
                return None
        return ''.join(result) if result else None

    # Continuous input: greedy left-to-right with digraph priority.

    result = []
    i = 0
    while i < len(lower):
        two = lower[i:i + 2]
        if two and two in extended:
            result.append(extended[two])
            i += 2
        elif lower[i] in extended:
            result.append(extended[lower[i]])
            i += 1
        else:
            return None  # unmappable character — give up

    return ''.join(result) if result else None


def parse_root_input(user_input: str) -> str | None:
    """Parse user input like 'K-T-B' or 'k t b' into Syriac root string.

    Accepts:
      - Dash-separated: K-T-B (triliteral) or G-SH (biliteral)
      - Space-separated: K T B or G SH
      - Digraphs: SH-L-M, KH-T-B, TH-Q-N, TS-L-M
      - Case-insensitive (except T for Teth)

    Returns Syriac root string (2 or 3 chars) or None if invalid.
    """
    user_input = user_input.strip()
    if not user_input:
        return None

    # Split by dash or space
    if '-' in user_input:
        parts = [p.strip() for p in user_input.split('-') if p.strip()]
    else:
        parts = user_input.split()

    if not (2 <= len(parts) <= 4):
        return None

    syriac_chars = []
    for part in parts:
        low = part.lower()
        # Check digraphs first
        if low in LATIN_TO_SYRIAC:
            syriac_chars.append(LATIN_TO_SYRIAC[low])
        elif part in LATIN_TO_SYRIAC:  # case-sensitive check (T for Teth)
            syriac_chars.append(LATIN_TO_SYRIAC[part])
        else:
            return None

    return ''.join(syriac_chars)


# --- Semitic sound correspondences ---
# Known cross-language consonant equivalences (Syriac Unicode pairs)
# Arabic s often corresponds to Hebrew/Syriac sh, etc.
SEMITIC_EQUIVALENCES = [
    ('\u0723', '\u072B'),  # ܣ Semkath (s) ↔ ܫ Shin (sh)
    ('\u072C', '\u071B'),  # ܬ Taw (th) ↔ ܛ Teth (T) — Arabic th/t
    ('\u0715', '\u072C'),  # ܕ Dalath (d) ↔ ܬ Taw (th) — Arabic dh/th
    ('\u0728', '\u0723'),  # ܨ Sadhe (ts) ↔ ܣ Semkath (s) — Arabic ṣ/s
]


def semitic_root_variants(root_syriac: str) -> list[str]:
    """Generate alternative Syriac root strings using Semitic sound correspondences.

    For example, if given ܣܠܡ (s-l-m), returns [ܫܠܡ (sh-l-m)] because
    Arabic s regularly corresponds to Hebrew/Syriac sh.

    Returns a list of alternative roots (not including the original).
    """
    if not root_syriac or not (2 <= len(root_syriac) <= 4):
        return []

    variants = set()
    chars = list(root_syriac)

    for pos in range(len(chars)):
        for a, b in SEMITIC_EQUIVALENCES:
            if chars[pos] == a:
                alt = chars.copy()
                alt[pos] = b
                variant = ''.join(alt)
                if variant != root_syriac:
                    variants.add(variant)
            elif chars[pos] == b:
                alt = chars.copy()
                alt[pos] = a
                variant = ''.join(alt)
                if variant != root_syriac:
                    variants.add(variant)

    return list(variants)


# --- Hebrew Consonants ---
HEBREW_CONSONANTS = frozenset([
    '\u05D0',  # א Alef
    '\u05D1',  # ב Bet
    '\u05D2',  # ג Gimel
    '\u05D3',  # ד Dalet
    '\u05D4',  # ה He
    '\u05D5',  # ו Vav
    '\u05D6',  # ז Zayin
    '\u05D7',  # ח Het
    '\u05D8',  # ט Tet
    '\u05D9',  # י Yod
    '\u05DA',  # ך Kaf final
    '\u05DB',  # כ Kaf
    '\u05DC',  # ל Lamed
    '\u05DD',  # ם Mem final
    '\u05DE',  # מ Mem
    '\u05DF',  # ן Nun final
    '\u05E0',  # נ Nun
    '\u05E1',  # ס Samekh
    '\u05E2',  # ע Ayin
    '\u05E3',  # ף Pe final
    '\u05E4',  # פ Pe
    '\u05E5',  # ץ Tsadi final
    '\u05E6',  # צ Tsadi
    '\u05E7',  # ק Qof
    '\u05E8',  # ר Resh
    '\u05E9',  # ש Shin
    '\u05EA',  # ת Tav
])

# Hebrew -> Syriac mapping (for cross-script root normalization)
HEBREW_TO_SYRIAC = {
    '\u05D0': '\u0710',  # א -> ܐ
    '\u05D1': '\u0712',  # ב -> ܒ
    '\u05D2': '\u0713',  # ג -> ܓ
    '\u05D3': '\u0715',  # ד -> ܕ
    '\u05D4': '\u0717',  # ה -> ܗ
    '\u05D5': '\u0718',  # ו -> ܘ
    '\u05D6': '\u0719',  # ז -> ܙ
    '\u05D7': '\u071A',  # ח -> ܚ
    '\u05D8': '\u071B',  # ט -> ܛ
    '\u05D9': '\u071D',  # י -> ܝ
    '\u05DA': '\u071F',  # ך -> ܟ (final kaf)
    '\u05DB': '\u071F',  # כ -> ܟ
    '\u05DC': '\u0720',  # ל -> ܠ
    '\u05DD': '\u0721',  # ם -> ܡ (final mem)
    '\u05DE': '\u0721',  # מ -> ܡ
    '\u05DF': '\u0722',  # ן -> ܢ (final nun)
    '\u05E0': '\u0722',  # נ -> ܢ
    '\u05E1': '\u0723',  # ס -> ܣ
    '\u05E2': '\u0725',  # ע -> ܥ
    '\u05E3': '\u0726',  # ף -> ܦ (final pe)
    '\u05E4': '\u0726',  # פ -> ܦ
    '\u05E5': '\u0728',  # ץ -> ܨ (final tsadi)
    '\u05E6': '\u0728',  # צ -> ܨ
    '\u05E7': '\u0729',  # ק -> ܩ
    '\u05E8': '\u072A',  # ר -> ܪ
    '\u05E9': '\u072B',  # ש -> ܫ
    '\u05EA': '\u072C',  # ת -> ܬ
}

# Hebrew weak letters (matres lectionis)
HEBREW_WEAK = frozenset(['\u05D0', '\u05D5', '\u05D9', '\u05D4'])  # א ו י ה


def syriac_consonants_of(word: str) -> str:
    """Extract only the Syriac consonant characters from a word."""
    return ''.join(ch for ch in word if ch in SYRIAC_CONSONANTS)


def hebrew_consonants_of(word: str) -> str:
    """Extract only the Hebrew consonant characters from a word.
    Normalizes final forms to regular forms."""
    FINAL_TO_REGULAR = {
        '\u05DA': '\u05DB',  # ך -> כ
        '\u05DD': '\u05DE',  # ם -> מ
        '\u05DF': '\u05E0',  # ן -> נ
        '\u05E3': '\u05E4',  # ף -> פ
        '\u05E5': '\u05E6',  # ץ -> צ
    }
    result = []
    for ch in word:
        if ch in HEBREW_CONSONANTS:
            result.append(FINAL_TO_REGULAR.get(ch, ch))
    return ''.join(result)


def hebrew_to_syriac(text: str) -> str:
    """Convert Hebrew square script text to Syriac Unicode.
    Used for cross-script root normalization."""
    result = []
    for ch in text:
        if ch in HEBREW_TO_SYRIAC:
            result.append(HEBREW_TO_SYRIAC[ch])
        elif ch == ' ':
            result.append(' ')
    return ''.join(result)


def normalize_root_to_latin(root_text: str) -> str:
    """Convert a root in any script (Syriac, Hebrew, Arabic) to Latin key.
    E.g., ܫܠܡ -> 'sh-l-m', שלם -> 'sh-l-m', سلم -> 's-l-m'
    Returns dash-separated Latin transliteration."""
    script = detect_script(root_text)
    if script == 'syriac':
        parts = [SYRIAC_TO_LATIN.get(ch, '') for ch in root_text if ch in SYRIAC_CONSONANTS]
    elif script == 'hebrew':
        cons = hebrew_consonants_of(root_text)
        parts = [HEBREW_TO_LATIN.get(ch, '') for ch in cons]
    elif script == 'arabic':
        parts = [ARABIC_TO_LATIN.get(ch, '') for ch in root_text if ch in ARABIC_TO_LATIN]
    else:
        return root_text.lower()
    return '-'.join(p for p in parts if p)


def detect_script(text: str) -> str:
    """Detect the script of the input text.

    Returns 'hebrew', 'arabic', 'syriac', or 'latin'.
    """
    for ch in text:
        cp = ord(ch)
        if 0x0590 <= cp <= 0x05FF:
            return 'hebrew'
        if 0x0600 <= cp <= 0x06FF or 0xFB50 <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            return 'arabic'
        if 0x0700 <= cp <= 0x074F:
            return 'syriac'
    return 'latin'


def strip_diacritics(text: str) -> str:
    """Remove Hebrew niqqud and Arabic tashkil diacritics from text.

    Hebrew niqqud: U+0591–U+05BD, U+05BF, U+05C1–U+05C2, U+05C4–U+05C5, U+05C7
    Arabic tashkil: U+064B–U+065F, U+0670, U+06D6–U+06DC, U+06DF–U+06E4, U+06E7–U+06E8
    """
    result = []
    for ch in text:
        cp = ord(ch)
        # Skip Hebrew niqqud
        if 0x0591 <= cp <= 0x05BD or cp == 0x05BF or cp in (0x05C1, 0x05C2, 0x05C4, 0x05C5, 0x05C7):
            continue
        # Skip Arabic tashkil
        if 0x064B <= cp <= 0x065F or cp == 0x0670:
            continue
        result.append(ch)
    return ''.join(result)
