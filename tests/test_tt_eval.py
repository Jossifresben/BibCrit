from translation_technique.gold import select_sample, agreement, mark_agreed, precision_recall


def test_select_sample_stratified_and_deterministic():
    refs = [f'Deuteronomy {c}:{v}' for c in range(1, 35) for v in range(1, 30)]
    s1, s2 = select_sample(refs, 200, 7), select_sample(refs, 200, 7)
    assert s1 == s2 and len(s1) == 200 and len(set(s1)) == 200
    chapters = {r.split(' ')[1].split(':')[0] for r in s1}
    assert len(chapters) == 34
    assert s1 == sorted(s1, key=lambda r: tuple(int(x) for x in r.split(' ')[1].split(':')))


def _g(ref, node, pos, reader):
    return {'ref': ref, 'heb_node': node, 'heb_lex': 'X', 'heb_word': 'x', 'heb_gloss': 'x', 'heb_feats': None,
            'syr_position': pos, 'syr_lemma': 'y' if pos else None, 'syr_source': None,
            'kind': 'one-one' if pos else 'null', 'reader': reader, 'agreed': None}


def test_agreement_and_mark():
    rows = [_g('r', 1, 1, 'jossi'), _g('r', 2, 2, 'jossi'), _g('r', 3, None, 'jossi'),
            _g('r', 1, 1, 'model'), _g('r', 2, 5, 'model'), _g('r', 3, None, 'model')]
    a = agreement(rows)
    assert a == {'verses': 1, 'links_jossi': 3, 'links_model': 3, 'agreed': 2, 'agreement': 2 / 3}
    marked = mark_agreed(rows)
    assert [r['agreed'] for r in marked] == [True, False, True, True, False, True]


def test_precision_recall_against_agreed_subset():
    gold = mark_agreed([_g('r', 1, 1, 'jossi'), _g('r', 2, 2, 'jossi'), _g('r', 1, 1, 'model'), _g('r', 2, 2, 'model'),
                        _g('r', 3, 3, 'jossi'), _g('r', 3, 4, 'model')])
    pred = [{'ref': 'r', 'heb_node': 1, 'syr_position': 1, 'kind': 'one-one'},
            {'ref': 'r', 'heb_node': 2, 'syr_position': 9, 'kind': 'one-one'},
            {'ref': 'r', 'heb_node': 3, 'syr_position': 3, 'kind': 'one-one'},   # not in agreed subset → ignored
            {'ref': 'r', 'heb_node': 4, 'syr_position': None, 'kind': 'null'}]
    pr = precision_recall(pred, gold)
    assert pr['n_gold'] == 2 and pr['n_pred'] == 2
    assert pr['precision'] == 0.5 and pr['recall'] == 0.5
