# tests/test_divergence.py
import pytest
from biblical_core.divergence import (
    DivergenceRecord, Hypothesis,
    confidence_tier, parse_claude_response,
    format_sbl_footnote, format_bibtex,
)


def _sample_data() -> dict:
    return {
        'divergences': [
            {
                'mt_word': 'הָעַלְמָה',
                'lxx_word': 'παρθένος',
                'divergence_type': 'theological_tendency',
                'confidence': 0.82,
                'hypotheses': [
                    {'type': 'theological_tendency', 'confidence': 0.82,
                     'explanation': 'Translator chose parthenos for messianic connotation.'},
                    {'type': 'translation_idiom', 'confidence': 0.41,
                     'explanation': 'Semantic overlap between almah and parthenos.'},
                ],
                'dss_witness': '1QIsa-a agrees with MT (hāʿalmāh)',
                'citations': ['Tov (2012) §8.3', 'Wevers (1993) p.112'],
                'analysis_technical': 'Scholarly analysis text.',
                'analysis_plain': 'Plain language text.',
            },
            {
                'mt_word': 'וְקָרָאת',
                'lxx_word': 'καλέσεις',
                'divergence_type': 'grammatical_shift',
                'confidence': 0.61,
                'hypotheses': [
                    {'type': 'grammatical_shift', 'confidence': 0.61,
                     'explanation': '3rd to 2nd person shift.'},
                ],
                'dss_witness': None,
                'citations': [],
                'analysis_technical': 'Grammatical analysis.',
                'analysis_plain': 'Plain version.',
            },
        ],
        'summary_technical': 'Overall summary.',
        'summary_plain': 'Plain summary.',
    }


def test_confidence_tier_high():
    assert confidence_tier(0.82) == 'HIGH'
    assert confidence_tier(0.75) == 'HIGH'
    assert confidence_tier(1.0) == 'HIGH'


def test_confidence_tier_medium():
    assert confidence_tier(0.61) == 'MEDIUM'
    assert confidence_tier(0.45) == 'MEDIUM'
    assert confidence_tier(0.74) == 'MEDIUM'


def test_confidence_tier_low():
    assert confidence_tier(0.12) == 'LOW'
    assert confidence_tier(0.0) == 'LOW'
    assert confidence_tier(0.44) == 'LOW'


def test_parse_returns_divergence_records():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    assert len(records) == 2
    assert all(isinstance(r, DivergenceRecord) for r in records)


def test_parse_fills_all_fields():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    r = records[0]
    assert r.reference == 'Isaiah 7:14'
    assert r.mt_word == 'הָעַלְמָה'
    assert r.lxx_word == 'παρθένος'
    assert r.divergence_type == 'theological_tendency'
    assert r.confidence == 0.82
    assert len(r.hypotheses) == 2
    assert r.dss_witness == '1QIsa-a agrees with MT (hāʿalmāh)'
    assert r.citations == ['Tov (2012) §8.3', 'Wevers (1993) p.112']


def test_parse_sorts_by_confidence_descending():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    assert records[0].confidence >= records[1].confidence


def test_parse_hypothesis_fields():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    h = records[0].hypotheses[0]
    assert isinstance(h, Hypothesis)
    assert h.type == 'theological_tendency'
    assert h.confidence == 0.82
    assert 'parthenos' in h.explanation


def test_format_sbl_footnote_contains_key_info():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    footnote = format_sbl_footnote(records[0])
    assert 'Isaiah 7:14' in footnote
    assert 'הָעַלְמָה' in footnote
    assert 'παρθένος' in footnote
    assert 'Tov' in footnote


def test_format_sbl_footnote_includes_dss():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    footnote = format_sbl_footnote(records[0])
    assert '1QIsa-a' in footnote


def test_format_bibtex_structure():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    bibtex = format_bibtex(records[0])
    assert '@misc{' in bibtex
    assert 'note' in bibtex


def test_parse_empty_divergences():
    records = parse_claude_response({'divergences': []}, 'Isaiah 7:14')
    assert records == []


def test_discovery_ready_defaults_false():
    records = parse_claude_response(_sample_data(), 'Isaiah 7:14')
    assert all(not r.discovery_ready for r in records)
