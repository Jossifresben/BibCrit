"""Multi-tradition word-level corpus for biblical texts.

CSV schema (word-level, one row per word):
  book_order, book, chapter, verse, reference, position,
  word_text, lemma, morph, strong, manuscript, tradition
"""

import csv
import os
from dataclasses import dataclass


@dataclass
class VerseWord:
    """A single morphologically-tagged word in a biblical verse."""
    reference: str        # "Isaiah 7:14"
    tradition: str        # "MT" | "LXX" | "GNT" | "DSS"
    position: int         # 1-based word position in the verse
    word_text: str        # surface form with pointing/accents
    lemma: str            # dictionary form
    morph: str            # morphological tag string
    strong: str           # Strong's number (H#### or G####)
    manuscript: str       # "Leningrad" | "Vaticanus" | "1QIsa-a" ...


class BiblicalCorpus:
    """Loads one or more biblical tradition CSVs and provides verse/word access.

    Each tradition (MT, LXX, GNT, DSS) lives in its own subdirectory under
    data_dir/corpora/<tradition_dir>/. Every CSV file in a tradition directory
    is loaded.

    Tradition directory mapping:
      MT  → corpora/mt_etcbc/
      LXX → corpora/lxx_stepbible/
      GNT → corpora/gnt_opengnt/
      DSS → corpora/dss/
    """

    _TRADITION_DIRS: dict = {
        'MT':  'mt_etcbc',
        'LXX': 'lxx_stepbible',
        'GNT': 'gnt_opengnt',
        'DSS': 'dss',
    }

    def __init__(self) -> None:
        # (reference, tradition) → sorted list of VerseWord
        self._words: dict = {}
        self._data_dir = None
        self._loaded: bool = False

    def set_data_dir(self, data_dir: str) -> None:
        """Set base data directory. Must be called before load_all()."""
        self._data_dir = data_dir
        self._loaded = False

    def load_all(self) -> None:
        """Load all available traditions. Safe to call multiple times."""
        if self._loaded:
            return
        if not self._data_dir:
            raise RuntimeError('Call set_data_dir() before load_all()')

        corpora_dir = os.path.join(self._data_dir, 'corpora')
        for tradition, subdir in self._TRADITION_DIRS.items():
            path = os.path.join(corpora_dir, subdir)
            if os.path.isdir(path):
                self._load_tradition_dir(path, tradition)

        # Sort each verse's words by position
        for key in self._words:
            self._words[key].sort(key=lambda w: w.position)

        self._loaded = True

    def _load_tradition_dir(self, directory: str, tradition: str) -> None:
        for filename in sorted(os.listdir(directory)):
            if filename.endswith('.csv'):
                self._load_csv(os.path.join(directory, filename), tradition)

    def _load_csv(self, path: str, tradition: str) -> None:
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
                    lemma=row['lemma'],
                    morph=row['morph'],
                    strong=row['strong'],
                    manuscript=row['manuscript'],
                )
                key = (row['reference'], tradition)
                if key not in self._words:
                    self._words[key] = []
                self._words[key].append(word)

    # ── Query API ──────────────────────────────────────────────────────────

    def get_verse_words(self, reference: str, tradition: str) -> list:
        """Return words for a verse in a given tradition, ordered by position."""
        self.load_all()
        return list(self._words.get((reference, tradition), []))

    def get_verse_text(self, reference: str, tradition: str) -> str:
        """Return all words joined by spaces (surface text of the verse)."""
        return ' '.join(w.word_text for w in self.get_verse_words(reference, tradition))

    def available_traditions(self, reference: str) -> list:
        """Return which traditions have data for this reference."""
        self.load_all()
        return [trad for (ref, trad) in self._words if ref == reference]

    def get_books(self, tradition: str) -> list:
        """Return distinct book names that have data in this tradition."""
        self.load_all()
        seen = set()
        result = []
        for (ref, trad) in self._words:
            if trad != tradition:
                continue
            book = _book_from_ref(ref)
            if book not in seen:
                seen.add(book)
                result.append(book)
        return result

    def get_chapters(self, book: str, tradition: str) -> list:
        """Return sorted chapter numbers for a book in this tradition."""
        self.load_all()
        chapters = set()
        for (ref, trad) in self._words:
            if trad != tradition:
                continue
            if _book_from_ref(ref) != book:
                continue
            chapters.add(_chapter_from_ref(ref))
        return sorted(chapters)

    def get_verses(self, book: str, chapter: int, tradition: str) -> list:
        """Return sorted verse numbers for a book+chapter in this tradition."""
        self.load_all()
        prefix = f'{book} {chapter}:'
        verses = set()
        for (ref, trad) in self._words:
            if trad != tradition:
                continue
            if not ref.startswith(prefix):
                continue
            verses.add(int(ref[len(prefix):]))
        return sorted(verses)


# ── Internal helpers ───────────────────────────────────────────────────────

def _book_from_ref(reference: str) -> str:
    """'Isaiah 7:14' → 'Isaiah'"""
    idx = reference.rfind(' ')
    return reference[:idx] if idx != -1 else reference


def _chapter_from_ref(reference: str) -> int:
    """'Isaiah 7:14' → 7"""
    idx = reference.rfind(' ')
    chv = reference[idx + 1:] if idx != -1 else reference
    return int(chv.split(':')[0])
