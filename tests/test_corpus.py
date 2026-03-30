# tests/test_corpus.py
import os
import pytest
from biblical_core.corpus import BiblicalCorpus, VerseWord

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


def make_corpus() -> BiblicalCorpus:
    c = BiblicalCorpus()
    c.set_data_dir(FIXTURES)
    c.load_all()
    return c


def test_load_mt_words():
    corpus = make_corpus()
    words = corpus.get_verse_words('Isaiah 7:14', 'MT')
    assert len(words) > 0
    assert all(w.tradition == 'MT' for w in words)


def test_load_lxx_words():
    corpus = make_corpus()
    words = corpus.get_verse_words('Isaiah 7:14', 'LXX')
    assert len(words) > 0
    assert all(w.tradition == 'LXX' for w in words)


def test_words_ordered_by_position():
    corpus = make_corpus()
    words = corpus.get_verse_words('Isaiah 7:14', 'MT')
    positions = [w.position for w in words]
    assert positions == sorted(positions)


def test_get_verse_text_joins_words():
    corpus = make_corpus()
    text = corpus.get_verse_text('Isaiah 7:14', 'MT')
    assert 'הָעַלְמָה' in text


def test_get_books_returns_isaiah():
    corpus = make_corpus()
    books = corpus.get_books('MT')
    assert 'Isaiah' in books


def test_get_chapters_for_book():
    corpus = make_corpus()
    chapters = corpus.get_chapters('Isaiah', 'MT')
    assert 7 in chapters


def test_get_verses_for_chapter():
    corpus = make_corpus()
    verses = corpus.get_verses('Isaiah', 7, 'MT')
    assert 14 in verses


def test_available_traditions_lists_both():
    corpus = make_corpus()
    traditions = corpus.available_traditions('Isaiah 7:14')
    assert 'MT' in traditions
    assert 'LXX' in traditions


def test_unknown_reference_returns_empty():
    corpus = make_corpus()
    words = corpus.get_verse_words('Obadiah 99:99', 'MT')
    assert words == []


def test_verse_word_fields():
    corpus = make_corpus()
    word = corpus.get_verse_words('Isaiah 7:14', 'MT')[0]
    assert isinstance(word, VerseWord)
    assert word.reference == 'Isaiah 7:14'
    assert word.word_text != ''
    assert word.lemma != ''
    assert word.manuscript != ''
