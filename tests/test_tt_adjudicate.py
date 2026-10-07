# tests/test_tt_adjudicate.py
import json
from translation_technique.adjudicate import (
    lemma_prompt, parse_lemma_response, link_prompt, parse_link_response,
    merge_lemma_annotations, merge_link_annotations, recompute_kinds, restore_orphans,
)


def test_lemma_prompt_mentions_every_form_and_demands_json():
    p = lemma_prompt([{'norm': 'ܘܬܡܚܐ', 'ref': 'Deuteronomy 1:1', 'verse_text': 'ܐ ܘܬܡܚܐ ܒ'}])
    assert 'ܘܬܡܚܐ' in p and 'JSON' in p and 'confidence' in p


def test_parse_lemma_response_accepts_valid_and_rejects_invalid():
    batch = [{'norm': 'ܘܬܡܚܐ', 'ref': 'Deuteronomy 1:1', 'verse_text': ''},
             {'norm': 'ܐܫܟܚܗ', 'ref': 'Deuteronomy 1:2', 'verse_text': ''}]
    text = json.dumps([
        {'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'verb', 'confidence': 0.7},
        {'norm': 'ܐܫܟܚܗ', 'lemma': 'eshkah', 'pos': 'verb', 'confidence': 0.9},      # not Syriac script
        {'norm': 'ܙܙܙ', 'lemma': 'ܙܙܙ', 'pos': 'verb', 'confidence': 0.9},             # not in batch
        {'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'thing', 'confidence': 0.7},          # bad pos
    ])
    acc = parse_lemma_response(text, batch)
    assert acc == [{'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'verb', 'confidence': 0.7}]


def test_parse_lemma_response_tolerates_code_fence_and_garbage():
    batch = [{'norm': 'ܘܬܡܚܐ', 'ref': 'r', 'verse_text': ''}]
    assert parse_lemma_response('```json\n[{"norm":"ܘܬܡܚܐ","lemma":"ܡܚܐ","pos":"verb","confidence":0.5}]\n```', batch)
    assert parse_lemma_response('not json', batch) == []


def test_link_prompt_and_parse_quarantines_bad_positions():
    batch = [{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'heb_word': 'וַיֵּרֶד', 'heb_lex': 'JRD[', 'heb_gloss': 'descend',
              'syr_tokens': [{'position': 1, 'form': 'ܘܢܚܬ'}, {'position': 2, 'form': 'ܡܢ'}]}]
    p = link_prompt(batch)
    assert 'JRD[' in p and 'ܘܢܚܬ' in p
    text = json.dumps([{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': 9},
                       {'ref': 'Deuteronomy 1:1', 'heb_node': 99, 'syr_position': 1}])
    assert parse_link_response(text, batch) == []
    text = json.dumps([{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': 1}])
    assert parse_link_response(text, batch) == [{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': 1}]
    text = json.dumps([{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': None}])
    assert parse_link_response(text, batch) == [{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': None}]


def test_merge_lemma_annotations_only_touches_unresolved():
    rows = [{'ref': 'r', 'position': 1, 'form': 'ܘܬܡܚܐ', 'norm': 'ܘܬܡܚܐ', 'lemma': None, 'pos': None,
             'source': 'unresolved', 'rule': None, 'candidates': [], 'confidence': 0.0},
            {'ref': 'r', 'position': 2, 'form': 'ܡܢ', 'norm': 'ܡܢ', 'lemma': 'ܡܢ', 'pos': 'particle',
             'source': 'sedra', 'rule': None, 'candidates': [], 'confidence': 1.0}]
    n = merge_lemma_annotations(rows, [{'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'verb', 'confidence': 0.7},
                                       {'norm': 'ܡܢ', 'lemma': 'X', 'pos': 'verb', 'confidence': 0.9}])
    assert n == 1
    assert rows[0]['source'] == 'model' and rows[0]['lemma'] == 'ܡܚܐ' and rows[0]['confidence'] == 0.7
    assert rows[1]['lemma'] == 'ܡܢ'


def test_merge_link_annotations_replaces_ibm1_row():
    rows = [{'ref': 'r', 'heb_node': 7, 'heb_lex': 'JRD[', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
             'syr_position': 2, 'syr_lemma': 'ܡܢ', 'syr_source': 'sedra', 'prob': 0.1, 'kind': 'one-one', 'source': 'ibm1'}]
    lookup = {('r', 1): ('ܢܚܬ', 'sedra'), ('r', 2): ('ܡܢ', 'sedra')}
    n = merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 7, 'syr_position': 1}], lookup)
    assert n == 1
    assert rows[0]['syr_position'] == 1 and rows[0]['syr_lemma'] == 'ܢܚܬ' and rows[0]['source'] == 'model' and rows[0]['prob'] is None
    rows[0]['source'] = 'ibm1'  # model rows are never re-touched; reset to exercise the null branch
    n = merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 7, 'syr_position': None}], lookup)
    assert rows[0]['kind'] == 'null' and rows[0]['syr_lemma'] is None and rows[0]['source'] == 'model'


def test_merge_link_annotations_collapses_duplicates_and_spares_model_rows():
    base = {'ref': 'r', 'heb_node': 7, 'heb_lex': 'L', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
            'syr_lemma': 'ܡܢ', 'syr_source': 'sedra', 'prob': 0.1, 'kind': 'one-many', 'source': 'ibm1'}
    rows = [dict(base, syr_position=2), dict(base, syr_position=3)]
    lookup = {('r', 1): ('ܢܚܬ', 'sedra')}
    n = merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 7, 'syr_position': 1}], lookup)
    assert n == 1 and len(rows) == 1 and rows[0]['syr_position'] == 1 and rows[0]['source'] == 'model'
    keep = [dict(base, syr_position=2, source='model')]
    assert merge_link_annotations(keep, [{'ref': 'r', 'heb_node': 7, 'syr_position': 1}], lookup) == 0
    assert keep[0]['syr_position'] == 2


def test_parsers_reject_wrong_types_without_raising():
    batch = [{'ref': 'r', 'heb_node': 7, 'heb_word': 'w', 'heb_lex': 'L', 'heb_gloss': 'g',
              'syr_tokens': [{'position': 1, 'form': 'ܐ'}]}]
    for bad in (True, 1.0, [1], '1'):
        assert parse_link_response(json.dumps([{'ref': 'r', 'heb_node': 7, 'syr_position': bad}]), batch) == []
    for bad in ([7], '7', True, 7.0):
        assert parse_link_response(json.dumps([{'ref': 'r', 'heb_node': bad, 'syr_position': 1}]), batch) == []
    lb = [{'norm': 'ܐܐ', 'ref': 'r', 'verse_text': ''}]
    for it in ({'norm': 'ܐܐ', 'lemma': 'ܐܐ\n', 'pos': 'verb', 'confidence': 0.5},
               {'norm': 'ܐܐ', 'lemma': 'ܐܐ', 'pos': 'verb', 'confidence': True},
               {'norm': ['ܐܐ'], 'lemma': 'ܐܐ', 'pos': 'verb', 'confidence': 0.5},
               {'norm': 'ܐܐ', 'lemma': 'ܐܐ', 'pos': ['verb'], 'confidence': 0.5}):
        assert parse_lemma_response(json.dumps([it]), lb) == []


def test_manifest_hash_order_independent_and_sensitive(tmp_path):
    from translation_technique.align import manifest_hash
    (tmp_path / 'a.jsonl').write_text('1\n')
    (tmp_path / 'b.jsonl').write_text('2\n')
    h = manifest_hash(str(tmp_path), ['a', 'b'])
    assert h == manifest_hash(str(tmp_path), ['b', 'a'])
    (tmp_path / 'b.jsonl').write_text('3\n')
    assert manifest_hash(str(tmp_path), ['a', 'b']) != h


def test_run_lemmas_respects_max_batches(tmp_path, monkeypatch):
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        'tt_adjudicate', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'tt_adjudicate.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from translation_technique.lemmas import write_jsonl
    (tmp_path / 'lemmas').mkdir()
    rows = [{'ref': 'r', 'position': i, 'form': f'f{i}', 'norm': f'ܐ{"ܒ" * i}', 'lemma': None, 'pos': None,
             'source': 'unresolved', 'rule': None, 'candidates': [], 'confidence': 0.0} for i in range(1, 8)]
    write_jsonl(str(tmp_path / 'lemmas' / 'x.jsonl'), rows)
    monkeypatch.setattr(mod, 'TT_DIR', str(tmp_path))
    monkeypatch.setattr(mod, 'LEMMA_BATCH', 2)
    monkeypatch.setattr(mod, '_verse_texts', lambda stem: {})

    class Fake:
        model_id = 'fake'
        calls = 0

        def complete(self, prompt):
            Fake.calls += 1
            return '[]', 'end_turn'

    stats = mod.run_lemmas('x', Fake(), False, max_batches=2)
    assert Fake.calls == 2 and stats == {'batches': 2, 'accepted': 0}
    Fake.calls = 0
    assert mod.run_lemmas('x', Fake(), False)['batches'] == 4


def _load_script():
    import importlib.util, os
    spec = importlib.util.spec_from_file_location(
        'tt_adjudicate', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'tt_adjudicate.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_update_manifest_recomputes_counts(tmp_path, monkeypatch):
    from translation_technique.lemmas import write_jsonl
    mod = _load_script()
    (tmp_path / 'align').mkdir()
    base = {'heb_node': 1, 'heb_lex': 'x', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {}}
    write_jsonl(str(tmp_path / 'align' / 'x.jsonl'), [
        dict(base, ref='r', kind='one-one', source='ibm1'), dict(base, ref='r', kind='one-one', source='model'),
        dict(base, ref='r', kind='null', source='ibm1')])
    (tmp_path / 'align' / 'pending.json').write_text(json.dumps([{'ref': 'r'}, {'ref': 'r'}]))
    (tmp_path / 'align' / 'manifest.json').write_text(json.dumps(
        {'books': ['x'], 'total_links': 99, 'pending_links': 99, 'model_links': 0, 'model_id': None, 'hash': ''}))
    monkeypatch.setattr(mod, 'TT_DIR', str(tmp_path))
    mod._update_manifest('m')
    m = json.loads((tmp_path / 'align' / 'manifest.json').read_text())
    assert m['pending_links'] == 2 and m['total_links'] == 2 and m['model_links'] == 1 and m['model_id'] == 'm'


def test_run_links_respects_max_batches_and_summary(tmp_path, monkeypatch, capsys):
    from translation_technique.lemmas import write_jsonl
    mod = _load_script()
    (tmp_path / 'align').mkdir()
    (tmp_path / 'lemmas').mkdir()
    refs = [f'Deuteronomy 1:{i}' for i in range(1, 4)]
    pend = [{'ref': r, 'heb_node': 1, 'heb_word': 'w', 'heb_lex': 'x', 'heb_gloss': 'g'} for r in refs]
    (tmp_path / 'align' / 'pending.json').write_text(json.dumps(pend))
    write_jsonl(str(tmp_path / 'lemmas' / 'deuteronomy.jsonl'), [
        {'ref': r, 'position': 1, 'form': 'f', 'lemma': 'l', 'source': 'sedra'} for r in refs])
    write_jsonl(str(tmp_path / 'align' / 'deuteronomy.jsonl'), [
        {'ref': r, 'heb_node': 1, 'heb_lex': 'x', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
         'syr_position': None, 'syr_lemma': None, 'syr_source': None, 'kind': 'null', 'source': 'ibm1'} for r in refs])
    (tmp_path / 'align' / 'manifest.json').write_text(json.dumps({'books': ['deuteronomy'], 'hash': ''}))
    monkeypatch.setattr(mod, 'TT_DIR', str(tmp_path))
    monkeypatch.setattr(mod, 'BATCH', 1)

    class Fake:
        model_id = 'fake'
        calls = 0

        def complete(self, prompt):
            Fake.calls += 1
            return '[]', 'end_turn'

    monkeypatch.setattr(mod, 'AnthropicAnnotator', lambda model: Fake())
    monkeypatch.setattr(mod, 'load_dotenv', lambda *a, **k: None)
    monkeypatch.setattr('sys.argv', ['tt_adjudicate.py', 'links', '--model', 'fake', '--max-batches', '2'])
    mod.main()
    assert Fake.calls == 2
    assert 'model=fake batches=2 accepted=0' in capsys.readouterr().out


def _link(node, pos, **kw):
    d = {'ref': 'r', 'heb_node': node, 'heb_lex': 'L', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
         'syr_position': pos, 'syr_lemma': f'l{pos}', 'syr_source': 'sedra', 'prob': 0.2, 'kind': 'one-one', 'source': 'ibm1'}
    d.update(kw)
    return d


def test_repoint_keeps_old_syriac_position_as_null_row():
    rows = [_link(1, 2), _link(2, 3)]
    lookup = {('r', 1): ('l1', 'sedra'), ('r', 2): ('l2', 'sedra'), ('r', 3): ('l3', 'rule')}
    merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 1, 'syr_position': 1}], lookup)
    assert {r['syr_position'] for r in rows} == {1, 2, 3}
    orphan = [r for r in rows if r['heb_node'] is None]
    assert len(orphan) == 1 and orphan[0]['syr_position'] == 2 and orphan[0]['kind'] == 'null'
    assert orphan[0]['source'] == 'ibm1' and orphan[0]['syr_lemma'] == 'l2'
    assert restore_orphans(rows, lookup, {'r': {1, 2, 3}}) == 0  # idempotent


def test_recompute_kinds_shared_syriac_token_is_many_one():
    rows = [_link(1, 5), _link(2, 5), _link(3, 6), _link(3, 7), _link(4, None, kind='null')]
    recompute_kinds(rows)
    assert [r['kind'] for r in rows] == ['many-one', 'many-one', 'one-many', 'one-many', 'null']


def test_merge_onto_shared_token_marks_both_many_one():
    rows = [_link(1, 5), _link(2, 6)]
    lookup = {('r', 5): ('l5', 'sedra'), ('r', 6): ('l6', 'sedra')}
    merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 2, 'syr_position': 5}], lookup)
    linked = [r for r in rows if r['heb_node'] is not None]
    assert [r['kind'] for r in linked] == ['many-one', 'many-one']


def test_run_lemmas_refreshes_coverage_and_unresolved(tmp_path, monkeypatch):
    from translation_technique.lemmas import write_jsonl
    mod = _load_script()
    (tmp_path / 'lemmas').mkdir()
    mk = lambda i, src, norm: {'ref': 'Deuteronomy 1:1', 'position': i, 'form': norm, 'norm': norm, 'lemma': norm if src != 'unresolved' else None,
                               'pos': None, 'source': src, 'confidence': 1.0}
    write_jsonl(str(tmp_path / 'lemmas' / 'deuteronomy.jsonl'), [mk(1, 'sedra', 'ܐܒܐ'), mk(2, 'unresolved', 'ܐܒܓ'), mk(3, 'unresolved', 'ܐܒܕ')])
    (tmp_path / 'lemmas' / 'coverage.json').write_text(json.dumps({'amos': {'tokens': 5}}))
    monkeypatch.setattr(mod, 'TT_DIR', str(tmp_path))
    monkeypatch.setattr(mod, '_verse_texts', lambda stem: {})

    class Fake:
        def complete(self, prompt):
            return json.dumps([{'norm': 'ܐܒܓ', 'lemma': 'ܐܒܓ', 'pos': 'noun', 'confidence': 0.9}]), 'end_turn'

    mod.run_lemmas('deuteronomy', Fake(), False)
    cov = json.loads((tmp_path / 'lemmas' / 'coverage.json').read_text())
    assert cov['amos'] == {'tokens': 5}
    assert abs(cov['deuteronomy']['by_source_tokens']['model'] - 1 / 3) < 1e-9
    assert json.loads((tmp_path / 'lemmas' / 'unresolved.deuteronomy.json').read_text()) == ['ܐܒܕ']
