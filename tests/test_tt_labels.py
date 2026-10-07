import pytest
from translation_technique.labels import (
    stem_name, tense_name, clause_type_name, objc_name, prep_name, facet_value_label,
)


def test_stems():
    assert [stem_name(c) for c in ('qal', 'nif', 'pie', 'pua', 'hit', 'hif', 'hof', 'pol')] == \
        ['Qal', 'Niphal', 'Piel', 'Pual', 'Hitpael', 'Hiphil', 'Hophal', 'Polel']
    assert stem_name('NA') == 'not a verb' and stem_name('zzz') == 'zzz'


def test_tenses():
    assert tense_name('perf') == 'perfect (qatal)' and tense_name('wayq') == 'wayyiqtol'
    assert tense_name('infa') == 'infinitive absolute' and tense_name('NA') == 'not a verb'
    assert tense_name('weird') == 'weird'


@pytest.mark.parametrize('code,expected', [
    ('WayX', 'wayyiqtol, with explicit subject'),
    ('Way0', 'wayyiqtol, no explicit subject'),
    ('WQtX', 'we-qatal, with explicit subject'),
    ('xYq0', 'fronted element, yiqtol, no explicit subject'),
    ('xQtX', 'fronted element, qatal, with explicit subject'),
    ('NmCl', 'nominal clause'),
    ('Ptcp', 'participial clause'),
    ('ZYq0', 'asyndetic, yiqtol, no explicit subject'),
    ('WxQ0', 'we-, fronted element, qatal, no explicit subject'),
    ('XQtl', 'X-qatal (subject first)'),
    ('InfC', 'infinitive construct clause'),
    ('Voct', 'vocative'),
    ('Bogus', 'Bogus'),
])
def test_clause_types(code, expected):
    assert clause_type_name(code) == expected


def test_objc_and_prep():
    assert objc_name('Objc') == 'has an object phrase' and objc_name('none') == 'no object phrase'
    assert prep_name('>L') == 'אל to, towards' and prep_name('none') == 'no preposition'
    assert prep_name('XYZ') == 'XYZ'


def test_facet_value_label_dispatch():
    assert facet_value_label('vs', 'hif') == 'Hiphil'
    assert facet_value_label('book', 'deuteronomy') == 'deuteronomy'
