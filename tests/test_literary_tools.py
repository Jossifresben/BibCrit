import pytest
from biblical_core.claude_pipeline import (
    CHIASM_MODEL, SOURCE_MODEL,
    _CHIASM_SYSTEM, _SOURCE_SYSTEM,
)

def test_chiasm_constants_are_importable():
    assert isinstance(CHIASM_MODEL, str) and CHIASM_MODEL
    assert isinstance(_CHIASM_SYSTEM, str) and 'chiasm' in _CHIASM_SYSTEM.lower()

def test_source_constants_are_importable():
    assert isinstance(SOURCE_MODEL, str) and SOURCE_MODEL
    assert isinstance(_SOURCE_SYSTEM, str) and 'source' in _SOURCE_SYSTEM.lower()


from biblical_core.claude_pipeline import ClaudePipeline, CHIASM_MODEL


def make_pipeline(tmp_path) -> ClaudePipeline:
    return ClaudePipeline(data_dir=str(tmp_path), api_key='', cap_usd=5.0)


def test_analyze_chiasm_no_client_returns_error(tmp_path):
    p = make_pipeline(tmp_path)
    result = p.analyze_chiasm('Amos 5:1-17')
    assert 'error' in result
    assert result['elements'] == []


def test_analyze_chiasm_cache_roundtrip(tmp_path):
    p = make_pipeline(tmp_path)
    fake = {
        'passage': 'Amos 5:1-17',
        'structure_detected': True,
        'structure_type': 'concentric',
        'elements': [{'label': 'A', 'verses': '5:1-3', 'summary': 'Lament',
                      'text_excerpt': 'Fallen, no more', 'confidence': 0.88}],
        'pivot': {'label': 'X', 'verses': '5:8-9', 'summary': 'Doxology',
                  'theological_weight': "God's sovereignty grounds the ethics."},
        'correspondences': [],
        'overall_confidence': 0.85,
        'methodology_citations': 'Dorsey 1999 ch.11',
        'theological_significance': 'Test significance.',
        'scholarly_citations': 'Dorsey, Wolff.',
        'bibcrit_hypothesis': {'title': 'Doxology as pivot', 'reasoning': 'test', 'confidence': 0.82},
        'discovery_ready': True,
    }
    p.save_cache('Amos 5:1-17', 'chiasm', 'v1', CHIASM_MODEL, fake)
    cached = p.get_cached('Amos 5:1-17', 'chiasm', 'v1', CHIASM_MODEL)
    assert cached is not None
    assert cached['structure_type'] == 'concentric'
    assert cached['elements'][0]['label'] == 'A'


def test_analyze_chiasm_budget_cap_returns_error(tmp_path):
    p = ClaudePipeline(data_dir=str(tmp_path), api_key='fake-key', cap_usd=0.0)
    result = p.analyze_chiasm('Genesis 1:1-2:3')
    assert 'error' in result
    assert 'budget' in result['error'].lower() or 'cap' in result['error'].lower()
    assert result['elements'] == []


def test_analyze_source_no_client_returns_error(tmp_path):
    p = make_pipeline(tmp_path)
    result = p.analyze_source('Genesis 1:1-2:3')
    assert 'error' in result
    assert result['source_units'] == []


def test_analyze_source_cache_roundtrip(tmp_path):
    p = make_pipeline(tmp_path)
    fake = {
        'passage': 'Genesis 1:1-2:3',
        'framework': 'classic_documentary',
        'scope_note': 'Covers the first creation account.',
        'source_units': [
            {
                'verses': '1:1-2:3',
                'source': 'P',
                'confidence': 0.92,
                'divine_name_used': 'Elohim',
                'key_vocabulary': ['bara', 'wayyehi erev'],
                'theological_concerns': 'Creation by command; sabbath rest.',
                'structural_markers': '7-day framework; formulaic repetition.',
                'doublet_with': '2:4-25',
                'summary': 'Priestly creation account.',
            }
        ],
        'doublets': [{'unit_1_verses': '1:1-2:3', 'unit_2_verses': '2:4-25',
                      'description': 'Two creation accounts',
                      'significance': 'Classic J/P doublet.'}],
        'competing_positions': [],
        'framework_note': 'Classic Documentary Hypothesis.',
        'synthesis': 'P dominates the first account.',
        'bibcrit_hypothesis': {'title': 'P creation account in Genesis 1', 'reasoning': 'test', 'confidence': 0.9},
        'discovery_ready': False,
    }
    p.save_cache('Genesis 1:1-2:3', 'source', 'v1', SOURCE_MODEL, fake)
    cached = p.get_cached('Genesis 1:1-2:3', 'source', 'v1', SOURCE_MODEL)
    assert cached is not None
    assert cached['source_units'][0]['source'] == 'P'
    assert cached['doublets'][0]['unit_2_verses'] == '2:4-25'


def test_analyze_source_budget_cap_returns_error(tmp_path):
    p = ClaudePipeline(data_dir=str(tmp_path), api_key='fake-key', cap_usd=0.0)
    result = p.analyze_source('Exodus 19')
    assert 'error' in result
    assert result['source_units'] == []
