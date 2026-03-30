"""Multi-corpus CSV parser and word index builder for Aramaic corpora.

Supports loading multiple corpora (e.g., Peshitta NT, Peshitta OT, Biblical Aramaic)
with a unified interface. Each verse is tagged with a corpus_id for filtering.
"""

import csv
import json
import os
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class CorpusInfo:
    """Metadata for a loaded corpus."""
    corpus_id: str
    label: str
    csv_path: str
    verse_count: int = 0
    word_count: int = 0


class AramaicCorpus:
    """Loads one or more Aramaic CSV corpora and builds searchable word indexes.

    Each CSV must have columns: book_order, book, chapter, verse, reference, syriac
    """

    def __init__(self):
        self._occurrences: dict[str, list[str]] = {}  # word -> [reference, ...]
        self._total_words: int = 0
        self._verses: dict[str, str] = {}  # reference -> syriac text (last loaded wins)
        self._verses_by_corpus: dict[str, dict[str, str]] = {}  # corpus_id -> {ref: text}
        self._verse_corpus: dict[str, str] = {}  # reference -> corpus_id (last wins)
        self._verse_corpora: dict[str, list[str]] = {}  # reference -> [corpus_ids]
        self._verse_order: list[str] = []  # ordered references
        self._translations: dict[str, dict] = {}  # lang -> {ref: text}
        self._corpora: dict[str, CorpusInfo] = {}  # corpus_id -> info
        self._translations_dir: str | None = None
        self._loaded = False

    def add_corpus(self, corpus_id: str, label: str, csv_path: str) -> None:
        """Register a corpus to be loaded. Call load() after adding all corpora."""
        self._corpora[corpus_id] = CorpusInfo(
            corpus_id=corpus_id,
            label=label,
            csv_path=csv_path,
        )
        self._loaded = False  # force reload

    def set_translations_dir(self, path: str) -> None:
        """Set the directory containing translations_XX.json files."""
        self._translations_dir = path

    def load(self) -> None:
        """Parse all registered CSVs and build the word index."""
        if self._loaded:
            return

        # Clear any previous state
        self._occurrences.clear()
        self._verses.clear()
        self._verses_by_corpus.clear()
        self._verse_corpus.clear()
        self._verse_corpora.clear()
        self._verse_order.clear()
        self._total_words = 0

        seen_refs = set()

        for corpus_id, info in self._corpora.items():
            if not os.path.exists(info.csv_path):
                continue
            corpus_words = 0
            corpus_verses = 0
            self._verses_by_corpus[corpus_id] = {}

            with open(info.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    syriac_text = row['syriac'].strip()
                    if not syriac_text:
                        continue

                    reference = row['reference']

                    self._verses[reference] = syriac_text
                    self._verse_corpus[reference] = corpus_id
                    self._verses_by_corpus[corpus_id][reference] = syriac_text

                    # Track all corpora for this reference
                    if reference not in self._verse_corpora:
                        self._verse_corpora[reference] = []
                    self._verse_corpora[reference].append(corpus_id)

                    if reference not in seen_refs:
                        self._verse_order.append(reference)
                        seen_refs.add(reference)
                    corpus_verses += 1

                    words = syriac_text.split()
                    for word in words:
                        clean_word = word.strip()
                        if not clean_word:
                            continue
                        self._total_words += 1
                        corpus_words += 1
                        if clean_word not in self._occurrences:
                            self._occurrences[clean_word] = []
                        self._occurrences[clean_word].append(reference)

            info.verse_count = corpus_verses
            info.word_count = corpus_words

        self._loaded = True

    def get_corpus_ids(self) -> list[str]:
        """Return list of loaded corpus IDs."""
        return list(self._corpora.keys())

    def get_corpus_info(self, corpus_id: str) -> CorpusInfo | None:
        """Return metadata for a corpus."""
        return self._corpora.get(corpus_id)

    def get_verse_corpus(self, reference: str) -> str | None:
        """Return the corpus_id for a given verse reference."""
        self.load()
        return self._verse_corpus.get(reference)

    def get_unique_words(self, corpus_id: str | None = None) -> set[str]:
        """Return all unique surface forms, optionally filtered by corpus."""
        self.load()
        if corpus_id is None:
            return set(self._occurrences.keys())
        # Filter: only words that appear in the specified corpus
        corpus_refs = {ref for ref, cid in self._verse_corpus.items() if cid == corpus_id}
        words = set()
        for word, refs in self._occurrences.items():
            if any(r in corpus_refs for r in refs):
                words.add(word)
        return words

    def get_occurrences(self, word: str, corpus_id: str | None = None) -> list[str]:
        """Return all references where this word appears, optionally filtered."""
        self.load()
        refs = self._occurrences.get(word, [])
        if corpus_id is None:
            return refs
        return [r for r in refs if self._verse_corpus.get(r) == corpus_id]

    def word_frequency(self, corpus_id: str | None = None) -> Counter:
        """Return word frequency counts, optionally filtered by corpus."""
        self.load()
        if corpus_id is None:
            return Counter({word: len(refs) for word, refs in self._occurrences.items()})
        counter = Counter()
        for word, refs in self._occurrences.items():
            count = sum(1 for r in refs if self._verse_corpus.get(r) == corpus_id)
            if count > 0:
                counter[word] = count
        return counter

    def total_words(self, corpus_id: str | None = None) -> int:
        """Return total word tokens, optionally filtered by corpus."""
        self.load()
        if corpus_id is None:
            return self._total_words
        info = self._corpora.get(corpus_id)
        return info.word_count if info else 0

    def total_unique(self, corpus_id: str | None = None) -> int:
        """Return number of unique surface forms."""
        return len(self.get_unique_words(corpus_id))

    def get_books(self, corpus_id: str | None = None) -> list[tuple[str, int]]:
        """Return ordered list of (book_name, max_chapter) tuples."""
        self.load()
        books_max_ch: dict[str, int] = {}
        book_list: list[tuple[str, int]] = []
        for ref in self._verse_order:
            if corpus_id and corpus_id not in self._verse_corpora.get(ref, []):
                continue
            last_space = ref.rfind(' ')
            book = ref[:last_space]
            ch = int(ref[last_space + 1:].split(':')[0])
            if book not in books_max_ch:
                books_max_ch[book] = ch
                book_list.append((book, ch))
            elif ch > books_max_ch[book]:
                books_max_ch[book] = ch
        return [(b, books_max_ch[b]) for b, _ in book_list]

    def get_chapter_verses(self, book: str, chapter: int,
                           corpus_id: str | None = None) -> list[tuple[int, str, str]]:
        """Return list of (verse_number, reference, syriac_text) for a chapter."""
        self.load()
        results = []
        for ref, text in self._verses.items():
            if corpus_id and corpus_id not in self._verse_corpora.get(ref, []):
                continue
            last_space = ref.rfind(' ')
            if last_space == -1:
                continue
            book_part = ref[:last_space]
            if book_part != book:
                continue
            chv = ref[last_space + 1:]
            if ':' not in chv:
                continue
            ch_str, v_str = chv.split(':', 1)
            try:
                ch = int(ch_str)
                v = int(v_str)
            except ValueError:
                continue
            if ch == chapter:
                # Use corpus-specific text if filtering
                if corpus_id:
                    text = self._verses_by_corpus.get(corpus_id, {}).get(ref, text)
                results.append((v, ref, text))
        results.sort(key=lambda x: x[0])
        return results

    def get_verse_text(self, reference: str, corpus_id: str | None = None) -> str | None:
        """Return the text for a given verse reference.
        If corpus_id is given, returns text from that specific corpus."""
        self.load()
        if corpus_id:
            return self._verses_by_corpus.get(corpus_id, {}).get(reference)
        return self._verses.get(reference)

    def get_verse_corpora(self, reference: str) -> list[str]:
        """Return all corpus_ids that contain this reference."""
        self.load()
        return self._verse_corpora.get(reference, [])

    def get_adjacent_ref(self, reference: str, direction: int) -> str | None:
        """Return the reference for an adjacent verse (direction: -1 or +1)."""
        self.load()
        last_space = reference.rfind(' ')
        if last_space == -1:
            return None
        book_part = reference[:last_space]
        chv_part = reference[last_space + 1:]
        if ':' not in chv_part:
            return None
        ch_str, v_str = chv_part.split(':', 1)
        try:
            chapter = int(ch_str)
            verse = int(v_str)
        except ValueError:
            return None
        new_verse = verse + direction
        if new_verse < 1:
            return None
        new_ref = f"{book_part} {chapter}:{new_verse}"
        if new_ref in self._verses:
            return new_ref
        return None

    def get_verse_translation(self, reference: str, lang: str) -> str:
        """Return a verse translation from per-language translation files."""
        if lang not in self._translations:
            if self._translations_dir:
                lang_path = os.path.join(self._translations_dir, f'translations_{lang}.json')
            else:
                lang_path = ''
            if lang_path and os.path.exists(lang_path):
                with open(lang_path, 'r', encoding='utf-8') as f:
                    self._translations[lang] = json.load(f)
            else:
                self._translations[lang] = {}
        return self._translations.get(lang, {}).get(reference, '')

    def search_text(self, query: str, lang: str = 'en',
                    corpus_id: str | None = None) -> list[dict]:
        """Search verse translations (or Syriac corpus) for a substring.

        Returns list of {reference, syriac, translation, match_positions, corpus_id}.
        """
        self.load()
        results = []
        query_lower = query.lower()

        # Detect Syriac script (U+0710-U+074F)
        is_syriac = any('\u0710' <= ch <= '\u074f' for ch in query)

        if is_syriac:
            for ref in self._verse_order:
                if corpus_id and self._verse_corpus.get(ref) != corpus_id:
                    continue
                text = self._verses[ref]
                pos = text.find(query)
                if pos != -1:
                    positions = []
                    start = 0
                    while True:
                        idx = text.find(query, start)
                        if idx == -1:
                            break
                        positions.append([idx, idx + len(query)])
                        start = idx + 1
                    results.append({
                        'reference': ref,
                        'syriac': text,
                        'translation': '',
                        'match_positions': positions,
                        'match_type': 'syriac',
                        'corpus_id': self._verse_corpus.get(ref, ''),
                    })
                    if len(results) >= 500:
                        break
        else:
            translations = self._ensure_translations(lang)
            for ref in self._verse_order:
                if corpus_id and self._verse_corpus.get(ref) != corpus_id:
                    continue
                trans_text = translations.get(ref, '')
                if not trans_text:
                    continue
                trans_lower = trans_text.lower()
                pos = trans_lower.find(query_lower)
                if pos != -1:
                    positions = []
                    start = 0
                    while True:
                        idx = trans_lower.find(query_lower, start)
                        if idx == -1:
                            break
                        positions.append([idx, idx + len(query_lower)])
                        start = idx + 1
                    results.append({
                        'reference': ref,
                        'syriac': self._verses.get(ref, ''),
                        'translation': trans_text,
                        'match_positions': positions,
                        'match_type': 'translation',
                        'corpus_id': self._verse_corpus.get(ref, ''),
                    })
                    if len(results) >= 500:
                        break

        return results

    def _ensure_translations(self, lang: str) -> dict:
        """Load and return the translations dict for a language."""
        if lang not in self._translations:
            if self._translations_dir:
                lang_path = os.path.join(self._translations_dir, f'translations_{lang}.json')
            else:
                lang_path = ''
            if lang_path and os.path.exists(lang_path):
                with open(lang_path, 'r', encoding='utf-8') as f:
                    self._translations[lang] = json.load(f)
            else:
                self._translations[lang] = {}
        return self._translations.get(lang, {})


# Backward-compatible alias
PeshittaCorpus = AramaicCorpus
