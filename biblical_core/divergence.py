"""Divergence analysis data model and formatting utilities.

Parses Claude's JSON response into typed DivergenceRecord objects.
Provides confidence tier classification and academic export formatters.
"""

from dataclasses import dataclass, field


@dataclass
class Hypothesis:
    """A single ranked hypothesis for why a divergence exists."""
    type: str           # divergence_type string
    confidence: float   # 0.0 – 1.0
    explanation: str    # scholarly explanation


@dataclass
class DivergenceRecord:
    """One MT/LXX divergence with full scholarly analysis."""
    reference: str
    mt_word: str
    lxx_word: str
    divergence_type: str
    confidence: float
    hypotheses: list
    dss_witness: object   # str or None
    citations: list
    analysis_technical: str
    analysis_plain: str
    discovery_ready: bool = False


# ── Classification ─────────────────────────────────────────────────────────

def confidence_tier(score: float) -> str:
    """Return 'HIGH', 'MEDIUM', or 'LOW' for a confidence score."""
    if score >= 0.75:
        return 'HIGH'
    if score >= 0.45:
        return 'MEDIUM'
    return 'LOW'


# ── Parsing ────────────────────────────────────────────────────────────────

def parse_claude_response(data: dict, reference: str) -> list:
    """Parse Claude's JSON dict into a list of DivergenceRecord objects.

    Records are sorted by confidence descending (highest first).
    """
    records = []

    for div in data.get('divergences', []):
        hypotheses = [
            Hypothesis(
                type=h.get('type', ''),
                confidence=float(h.get('confidence', 0.0)),
                explanation=h.get('explanation', ''),
            )
            for h in div.get('hypotheses', [])
        ]
        records.append(DivergenceRecord(
            reference=reference,
            mt_word=div.get('mt_word', ''),
            lxx_word=div.get('lxx_word', ''),
            divergence_type=div.get('divergence_type', ''),
            confidence=float(div.get('confidence', 0.0)),
            hypotheses=hypotheses,
            dss_witness=div.get('dss_witness') or None,
            citations=div.get('citations', []),
            analysis_technical=div.get('analysis_technical', ''),
            analysis_plain=div.get('analysis_plain', ''),
            discovery_ready=bool(div.get('discovery_ready', False)),
        ))

    return sorted(records, key=lambda r: r.confidence, reverse=True)


# ── Export ─────────────────────────────────────────────────────────────────

def format_sbl_footnote(record: DivergenceRecord) -> str:
    """Format divergence as an SBL-style footnote string."""
    parts = [f'In {record.reference}, MT {record.mt_word} vs. LXX {record.lxx_word}.']

    if record.hypotheses:
        parts.append(record.hypotheses[0].explanation)

    if record.dss_witness:
        parts.append(f'DSS evidence: {record.dss_witness}.')

    if record.citations:
        parts.append(f'Cf. {"; ".join(record.citations)}.')

    return ' '.join(parts)


def format_bibtex(record: DivergenceRecord) -> str:
    """Format divergence as a BibTeX @misc entry."""
    key = (
        record.reference
        .replace(' ', '')
        .replace(':', '_')
        .replace('.', '')
    )
    note = format_sbl_footnote(record).replace('{', '(').replace('}', ')')
    return f'@misc{{{key},\n  note = {{{note}}}\n}}'
