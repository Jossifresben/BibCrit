"""Multi-tradition word-level corpus for biblical texts.

CSV schema (word-level, one row per word):
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition

Memory strategy: LAZY LOADING BY BOOK.
CSVs are not loaded at startup. Each book is loaded on first access and
cached in memory. This keeps peak memory well under 512 MB on a free
Render instance even with full OT + NT corpora on disk.
"""

import csv
import os
from collections import OrderedDict
from dataclasses import dataclass

# Maximum number of book-CSV files kept in memory simultaneously.
# Each file is roughly 1–3 MB of Python objects; 50 files ≈ 50–150 MB,
# leaving ample headroom on a 512 MB Render instance.
_LRU_CAP = 50


@dataclass(slots=True)
class VerseWord:
    """A single morphologically-tagged word in a biblical verse."""
    reference: str        # "Isaiah 7:14"
    tradition: str        # "MT" | "LXX" | "GNT" | "DSS" | "SP"
    position: int         # 1-based word position in the verse
    word_text: str        # surface form with pointing/accents
    lemma: str            # dictionary form
    morph: str            # morphological tag string
    strong: str           # Strong's number (H#### or G####)
    manuscript: str       # "Leningrad" | "Vaticanus" | "1QIsa-a" ...


class BiblicalCorpus:
    """Provides verse/word access across biblical traditions with lazy book loading.

    Each tradition (MT, LXX, GNT, DSS, SP) lives in its own subdirectory under
    data_dir/corpora/<tradition_dir>/. Books are loaded on first access only.

    Tradition directory mapping:
      MT  → corpora/mt_etcbc/
      LXX → corpora/lxx_stepbible/
      GNT → corpora/gnt_opengnt/
      DSS → corpora/dss/
      SP  → corpora/sp_etcbc/
    """

    _TRADITION_DIRS: dict = {
        'MT':   'mt_etcbc',
        'LXX':  'lxx_stepbible',
        'GNT':  'gnt_opengnt',
        'DSS':  'dss',
        'SP':   'sp_etcbc',
        'PESH': 'pesh_etcbc',
        'TARG': 'targ_sefaria',
        'VUL':  'vul_clementine',
    }

    def __init__(self) -> None:
        # (reference, tradition) → sorted list of VerseWord
        self._words: dict = {}
        self._data_dir: str | None = None
        # (tradition, book_stem) → csv_path   (built at set_data_dir time)
        self._file_index: dict = {}
        # (tradition, book_stem) → canonical book name
        self._book_names: dict = {}
        # (tradition, canonical_book_name) → csv_path  — primary lookup path
        self._canonical_to_path: dict = {}
        # LRU cache: file_path → frozenset of (reference, tradition) keys added.
        # Oldest entry is evicted when len exceeds _LRU_CAP.
        self._lru: OrderedDict = OrderedDict()

    def set_data_dir(self, data_dir: str) -> None:
        """Set base data directory and scan available files (no CSV data loaded)."""
        self._data_dir = data_dir
        self._words = {}
        self._file_index = {}
        self._book_names = {}
        self._lru = OrderedDict()
        self._build_file_index()

    # ── Index building (startup — reads filenames only, no word data) ──────

    def _build_file_index(self) -> None:
        """Scan tradition directories and index available CSV files.

        Reads only the first data row of each CSV to obtain the canonical
        book name (e.g. 'song_of_songs.csv' → 'Song of Songs').
        This is fast (~1 ms per file, ~150 files total).
        """
        corpora_dir = os.path.join(self._data_dir, 'corpora')
        for tradition, subdir in self._TRADITION_DIRS.items():
            path = os.path.join(corpora_dir, subdir)
            if not os.path.isdir(path):
                continue
            for filename in sorted(os.listdir(path)):
                if not filename.endswith('.csv'):
                    continue
                stem = filename[:-4]
                fpath = os.path.join(path, filename)
                self._file_index[(tradition, stem)] = fpath
                # Peek at first row to get canonical book name
                canonical = _canonical_book_from_csv(fpath)
                if canonical:
                    self._book_names[(tradition, stem)] = canonical
                    # Primary lookup: by canonical name (handles 1qisaa.csv → "Isaiah")
                    self._canonical_to_path[(tradition, canonical)] = fpath

    # ── Lazy loading ────────────────────────────────────────────────────────

    def _ensure_book_loaded(self, book: str, tradition: str) -> None:
        """Load the CSV for this (book, tradition) pair if not already cached.

        Uses canonical book name first (handles DSS where 1qisaa.csv → 'Isaiah'),
        then falls back to stem-based lookup for standard naming conventions.
        """
        # Primary: canonical-name index (handles DSS manuscript filenames)
        fpath = self._canonical_to_path.get((tradition, book))
        # Fallback: stem-based (e.g., 'genesis' → 'genesis.csv')
        if not fpath:
            fpath = self._file_index.get((tradition, _book_to_stem(book)))
        if fpath:
            if fpath in self._lru:
                self._lru.move_to_end(fpath)   # mark as recently used
            else:
                added_keys = self._load_csv(fpath, tradition)
                self._lru[fpath] = added_keys
                # Evict oldest entry when cap exceeded
                while len(self._lru) > _LRU_CAP:
                    _, evicted = self._lru.popitem(last=False)
                    for k in evicted:
                        self._words.pop(k, None)

    def _load_csv(self, path: str, tradition: str) -> set:
        """Read one CSV into self._words, sorting words by position.

        Returns the set of (reference, tradition) keys added, so the caller
        can register them in the LRU index for later eviction.
        """
        tmp: dict = {}
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get('word_text', '').strip():
                    continue
                word = VerseWord(
                    reference=row['reference'],
                    tradition=tradition,
                    position=int(row['position']),
                    word_text=row['word_text'],
                    lemma=row.get('lemma', ''),
                    morph=row.get('morph', ''),
                    strong=row.get('strong', ''),
                    manuscript=row.get('manuscript', ''),
                )
                key = (row['reference'], tradition)
                tmp.setdefault(key, []).append(word)

        added_keys: set = set()
        for key, words in tmp.items():
            words.sort(key=lambda w: w.position)
            self._words[key] = words
            added_keys.add(key)
        return added_keys

    # ── Public query API ────────────────────────────────────────────────────

    def get_verse_words(self, reference: str, tradition: str) -> list:
        """Return words for a verse in a given tradition, ordered by position."""
        ref = _norm_ref(reference)
        book = _book_from_ref(ref)
        self._ensure_book_loaded(book, tradition)
        return list(self._words.get((ref, tradition), []))

    def get_verse_text(self, reference: str, tradition: str) -> str:
        """Return all words joined by spaces (surface text of the verse)."""
        return ' '.join(w.word_text for w in self.get_verse_words(reference, tradition))

    def get_chapter_words(self, book: str, chapter: int, tradition: str) -> list:
        """Return all words in a chapter, in verse order.

        Used for chapter-level references (e.g. 'Genesis 5') where the corpus
        stores individual verse keys like 'Genesis 5:1', 'Genesis 5:2', …
        """
        verse_nums = self.get_verses(book, chapter, tradition)
        words = []
        for v in verse_nums:
            words.extend(self.get_verse_words(f'{book} {chapter}:{v}', tradition))
        return words

    def get_chapter_text(self, book: str, chapter: int, tradition: str) -> str:
        """Return all chapter words joined by spaces."""
        return ' '.join(w.word_text for w in self.get_chapter_words(book, chapter, tradition))

    def available_traditions(self, reference: str) -> list:
        """Return which traditions have data for this reference."""
        ref = _norm_ref(reference)
        book = _book_from_ref(ref)
        result = []
        for tradition in self._TRADITION_DIRS:
            self._ensure_book_loaded(book, tradition)
            if (ref, tradition) in self._words:
                result.append(tradition)
        return result

    def get_books(self, tradition: str) -> list:
        """Return distinct book names available in this tradition.

        Uses the file index — no full CSV loading required.
        """
        books = []
        for (trad, stem), name in sorted(self._book_names.items()):
            if trad == tradition:
                books.append(name)
        return sorted(set(books))

    def get_chapters(self, book: str, tradition: str) -> list:
        """Return sorted chapter numbers for a book in this tradition."""
        self._ensure_book_loaded(book, tradition)
        chapters: set = set()
        for (ref, trad) in self._words:
            if trad != tradition:
                continue
            if _book_from_ref(ref) != book:
                continue
            chapters.add(_chapter_from_ref(ref))
        return sorted(chapters)

    def get_verses(self, book: str, chapter: int, tradition: str) -> list:
        """Return sorted verse numbers for a book+chapter in this tradition."""
        self._ensure_book_loaded(book, tradition)
        prefix = f'{book} {chapter}:'
        verses: set = set()
        for (ref, trad) in self._words:
            if trad != tradition:
                continue
            if not ref.startswith(prefix):
                continue
            verses.add(int(ref[len(prefix):]))
        return sorted(verses)

    # Legacy compat: called by old code that expected load_all() ─────────────

    def load_all(self) -> None:  # pragma: no cover
        """Deprecated shim — lazy loading makes this a no-op.

        Kept for backward compatibility; individual books are loaded on demand.
        """
        pass


# ── Internal helpers ──────────────────────────────────────────────────────────

def _canonical_book_from_csv(path: str) -> str:
    """Read the first data row of a CSV and return the 'book' field value."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                return row.get('book', '')
    except Exception:
        pass
    return ''


def _book_to_stem(book: str) -> str:
    """Convert a canonical book name to its CSV filename stem.

    'Song of Songs' → 'song_of_songs'
    '1 Corinthians' → '1_corinthians'
    """
    return book.lower().replace(' ', '_').replace("'", '')


def _book_from_ref(reference: str) -> str:
    """'Isaiah 7:14' → 'Isaiah'"""
    idx = reference.rfind(' ')
    return reference[:idx] if idx != -1 else reference


def _chapter_from_ref(reference: str) -> int:
    """'Isaiah 7:14' → 7"""
    idx = reference.rfind(' ')
    chv = reference[idx + 1:] if idx != -1 else reference
    return int(chv.split(':')[0])


def _norm_ref(reference: str) -> str:
    """Normalize legacy book name variants to match ETCBC canonical names.

    'Psalm 22:1' → 'Psalms 22:1'  (ETCBC uses plural)
    """
    _ALIASES = {
        'Psalm ': 'Psalms ',
    }
    for alias, canonical in _ALIASES.items():
        if reference.startswith(alias):
            return canonical + reference[len(alias):]
    return reference
