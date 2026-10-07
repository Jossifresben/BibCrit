from translation_technique.lemmas import normalize_form, strip_affixes, AFFIX_RULES


def test_normalize_strips_seyame_and_dots():
    assert normalize_form('ܬܪ̈ܥܝܗܝܢ') == 'ܬܪܥܝܗܝܢ'
    assert normalize_form('ܕܩ̇ܛܠ') == 'ܕܩܛܠ'
    assert normalize_form('ܥܝܢܗ̇') == 'ܥܝܢܗ'


def test_normalize_leaves_plain_forms_alone():
    assert normalize_form('ܡܪܝܐ') == 'ܡܪܝܐ'


def test_normalize_strips_surrounding_whitespace():
    assert normalize_form(' ܡܢ ') == 'ܡܢ'


def test_strip_affixes_proclitic_waw_then_dalath():
    cands = strip_affixes('ܘܕܫܡܫܐ')
    ids = [c[0] for c in cands]
    forms = [c[1] for c in cands]
    assert 'ܕܫܡܫܐ' in forms          # after stripping ܘ
    assert 'ܫܡܫܐ' in forms           # after stripping ܘ then ܕ
    assert ids[0] == 'pre_waw'


def test_strip_affixes_suffix():
    cands = strip_affixes('ܥܝܢܗ')
    assert ('suf_h', 'ܥܝܢ') in cands


def test_strip_affixes_never_returns_empty_or_single_letter():
    for _, form in strip_affixes('ܘܠ'):
        assert len(form) >= 2


def test_affix_rules_order_is_waw_dalath_lamadh_beth_first():
    kinds = [(r[0], r[1]) for r in AFFIX_RULES[:4]]
    assert kinds == [('pre_waw', 'pre'), ('pre_dalath', 'pre'), ('pre_lamadh', 'pre'), ('pre_beth', 'pre')]
