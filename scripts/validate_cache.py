#!/usr/bin/env python3
"""
validate_cache.py — BibCrit cache validation via Anthropic Batch API

Runs an Opus critic pass on every cached analysis and stores a _validation
object in each cache JSON file.  Uses the Batch API (50% cheaper than live).

Usage:
    # Full batch — all unvalidated entries
    python scripts/validate_cache.py

    # Sample — first N entries (quick preview)
    python scripts/validate_cache.py --sample 5

    # Re-validate a specific tool
    python scripts/validate_cache.py --tool patristic

    # Submit only — don't wait (get batch ID, poll later)
    python scripts/validate_cache.py --submit-only

    # Poll an existing batch and write results
    python scripts/validate_cache.py --poll-batch msgbatch_XXXX

    # Re-run even entries that already have _validation
    python scripts/validate_cache.py --force
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

# ── Config ────────────────────────────────────────────────────────────────────
CACHE_DIR     = Path(__file__).parent.parent / 'data' / 'cache'
VALIDATION_MODEL = 'claude-opus-4-7'
MAX_TOKENS    = 2048

# Keys that are metadata, not analysis content — don't send to critic
_META_KEYS = {
    'cached_at', 'model_version', 'prompt_version', 'reference', 'book',
    'discovery_ready', 'cache_key', 'parse_error', 'parse_error_len',
    '_validation', 'mt_words', 'lxx_words', 'sp_words', 'dss_words',
}

# ── Critic prompt ─────────────────────────────────────────────────────────────
_SYSTEM = (
    "You are a senior biblical textual criticism expert auditing AI-generated "
    "analyses for factual accuracy and hallucination risk. Your job is to catch "
    "specific claims that could be wrong, invented, or over-confident."
)

_CRITIC_TEMPLATE = """\
Audit the following AI-generated biblical analysis for scholarly reliability.
Passage: {reference}

ANALYSIS:
{analysis_text}

Respond with ONLY valid JSON. No markdown fences. No trailing commas. Schema:
{{
  "reliability": "HIGH" | "MEDIUM" | "LOW",
  "confidence_note": "<one sentence summary of overall trustworthiness>",
  "flagged_claims": [
    {{
      "claim": "<exact short quote of the specific claim>",
      "risk": "HIGH" | "MEDIUM",
      "reason": "<why this may be wrong, fabricated, or unverifiable>"
    }}
  ],
  "safe_claims": ["<claims grounded in observable textual data>"],
  "recommendation": "PUBLISH_AS_IS" | "PUBLISH_WITH_CAVEAT" | "NEEDS_EXPERT_REVIEW"
}}

Be specifically skeptical of:
- Patristic citations: author + work + chapter/paragraph references (easily fabricated)
- Second Temple allusion claims: specific parallels to 1 Enoch, Jubilees, etc.
- Manuscript genealogy: dependency claims between specific MSS
- Scribal error identifications attributed to named scribes or dated precisely
- Source-layer assignments stated with more certainty than the evidence supports
- NT-OT quotation attributions where the NT author is debated

Do NOT flag:
- General methodological statements
- Claims verifiable directly from the MT/LXX text (word differences)
- Well-established scholarly positions (e.g. "LXX Isaiah is shorter than MT")
- Confidence ratings attached to the analysis itself
"""


def _parse_json_response(text: str) -> dict | None:
    """Robustly parse a JSON response that may have markdown fences, trailing commas, etc."""
    import re
    # Strip markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
    text = text.strip()
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Extract first {...} block
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if not m:
        return None
    candidate = m.group()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Remove trailing commas before } or ]
    cleaned = re.sub(r',\s*([}\]])', r'\1', candidate)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _infer_tool(data: dict) -> str:
    keys = set(data.keys())
    if 'citations' in keys or 'citation_count' in keys: return 'patristic'
    if 'divergences' in keys:                           return 'divergence'
    if 'reconstructed_words' in keys:                  return 'backtranslation'
    if 'dss_manuscripts' in keys:                      return 'dss'
    if 'figures' in keys:                              return 'numerical'
    if 'dimensions' in keys:                           return 'scribal'
    if 'stemma_nodes' in keys or 'archetype' in keys:  return 'genealogy'
    if 'source_layers' in keys or 'layers' in keys:   return 'source'
    if 'allusions' in keys:                            return 'stl'
    if 'structure_detected' in keys or 'elements' in keys: return 'chiasm'
    if 'revisions' in keys or 'theological_revisions' in keys: return 'theological'
    if 'nt_quotations' in keys or 'quotations' in keys: return 'nt_ot'
    if 'targum' in keys:                               return 'targum'
    return 'unknown'


def _build_analysis_text(data: dict) -> str:
    """Flatten the relevant analysis keys into a readable text block."""
    parts = []
    for k, v in data.items():
        if k in _META_KEYS:
            continue
        if isinstance(v, str) and v.strip():
            parts.append(f"[{k}]\n{v.strip()}")
        elif isinstance(v, list) and v:
            try:
                parts.append(f"[{k}]\n{json.dumps(v, ensure_ascii=False, indent=2)}")
            except Exception:
                pass
        elif isinstance(v, dict) and v:
            try:
                parts.append(f"[{k}]\n{json.dumps(v, ensure_ascii=False, indent=2)}")
            except Exception:
                pass
    return '\n\n'.join(parts)[:12000]  # cap at ~12k chars to stay within token budget


def _load_cache_files(tool_filter: str | None = None) -> list[tuple[Path, dict]]:
    """Return list of (path, data) for all valid cache entries."""
    entries = []
    for fn in sorted(CACHE_DIR.glob('*.json')):
        try:
            data = json.loads(fn.read_text(encoding='utf-8'))
        except Exception:
            continue
        # Skip non-analysis files (budget, stemma-only, etc.)
        if 'reference' not in data:
            continue
        if tool_filter and _infer_tool(data) != tool_filter:
            continue
        entries.append((fn, data))
    return entries


def _submit_batch(entries: list[tuple[Path, dict]],
                  force: bool = False) -> tuple[str, dict[str, Path]]:
    """Build and submit an Anthropic Message Batch. Returns (batch_id, id_to_path)."""
    client = anthropic.Anthropic()
    requests = []
    id_to_path: dict[str, Path] = {}

    for path, data in entries:
        if not force and '_validation' in data:
            continue  # already validated
        ref  = data.get('reference', 'unknown')
        text = _build_analysis_text(data)
        if not text.strip():
            continue

        prompt = _CRITIC_TEMPLATE.format(
            reference=ref,
            analysis_text=text,
        )
        custom_id = path.stem  # use cache filename (SHA256) as ID
        requests.append({
            'custom_id': custom_id,
            'params': {
                'model': VALIDATION_MODEL,
                'max_tokens': MAX_TOKENS,
                'system': _SYSTEM,
                'messages': [{'role': 'user', 'content': prompt}],
            },
        })
        id_to_path[custom_id] = path

    if not requests:
        print('Nothing to validate (all entries already have _validation). Use --force to re-run.')
        sys.exit(0)

    print(f'Submitting batch of {len(requests)} requests to {VALIDATION_MODEL}...')
    batch = client.messages.batches.create(requests=requests)
    print(f'Batch submitted: {batch.id}')
    print(f'Status: {batch.processing_status}')
    return batch.id, id_to_path


def _poll_and_write(batch_id: str, id_to_path: dict[str, Path],
                    poll_interval: int = 30) -> None:
    """Poll until the batch completes, then write _validation to each cache file."""
    client = anthropic.Anthropic()
    print(f'Polling batch {batch_id} every {poll_interval}s...')

    while True:
        batch = client.messages.batches.retrieve(batch_id)
        counts = batch.request_counts
        print(
            f'  [{datetime.now(timezone.utc).strftime("%H:%M:%S")}] '
            f'{batch.processing_status} — '
            f'processing={counts.processing} succeeded={counts.succeeded} '
            f'errored={counts.errored} canceled={counts.canceled}',
            flush=True,
        )
        if batch.processing_status == 'ended':
            break
        time.sleep(poll_interval)

    # Write results back to cache files
    succeeded = errored = skipped = 0
    flagged_summary = []

    for result in client.messages.batches.results(batch_id):
        path = id_to_path.get(result.custom_id)
        if not path or not path.exists():
            skipped += 1
            continue

        if result.result.type != 'succeeded':
            print(f'  ✗ {result.custom_id[:16]}… error: {result.result.type}')
            errored += 1
            continue

        raw_text = result.result.message.content[0].text.strip()

        # Parse the JSON response
        validation = _parse_json_response(raw_text)
        if validation is None:
            print(f'  ✗ {result.custom_id[:16]}… could not parse response')
            errored += 1
            continue

        validation['validated_at'] = datetime.now(timezone.utc).isoformat()
        validation['validated_by'] = VALIDATION_MODEL

        # Write back to cache file
        data = json.loads(path.read_text(encoding='utf-8'))
        data['_validation'] = validation
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        succeeded += 1

        # Collect flagged items for summary
        rel  = validation.get('reliability', '?')
        ref  = data.get('reference', result.custom_id[:16])
        tool = _infer_tool(data)
        n_flagged = len(validation.get('flagged_claims', []))
        rec = validation.get('recommendation', '?')

        if rel in ('LOW', 'MEDIUM') or n_flagged > 0:
            flagged_summary.append({
                'ref': ref, 'tool': tool, 'reliability': rel,
                'n_flagged': n_flagged, 'rec': rec,
                'note': validation.get('confidence_note', ''),
                'claims': validation.get('flagged_claims', [])[:2],
            })

    print(f'\n✓ Done — {succeeded} validated, {errored} errored, {skipped} skipped')

    # Print summary of flagged analyses
    if flagged_summary:
        flagged_summary.sort(key=lambda x: ('HIGH' not in x['reliability'], x['n_flagged']))
        print(f'\n{"─"*72}')
        print(f'FLAGGED ANALYSES ({len(flagged_summary)} entries need attention)')
        print(f'{"─"*72}')
        for entry in flagged_summary[:20]:  # cap at 20 for readability
            print(f'\n[{entry["reliability"]:6}] {entry["tool"]:15} {entry["ref"]}')
            print(f'         {entry["note"]}')
            print(f'         Recommendation: {entry["rec"]}  |  {entry["n_flagged"]} claim(s) flagged')
            for c in entry['claims']:
                print(f'         ⚠  [{c["risk"]}] {c["claim"][:80]}')
                print(f'              → {c["reason"][:100]}')
    else:
        print('\n✓ No analyses flagged — all HIGH reliability.')


def _print_sample(entries: list[tuple[Path, dict]], n: int) -> None:
    """Immediately validate N entries (no batch — live API) and print results."""
    client = anthropic.Anthropic()
    print(f'Sample validation of {n} entries (live API, no batch)...\n')

    for path, data in entries[:n]:
        ref  = data.get('reference', '?')
        tool = _infer_tool(data)
        text = _build_analysis_text(data)
        if not text.strip():
            print(f'  SKIP {ref} (no analysis content)')
            continue

        prompt = _CRITIC_TEMPLATE.format(reference=ref, analysis_text=text)
        print(f'  Validating [{tool:15}] {ref}... ', end='', flush=True)
        t0 = time.time()

        try:
            response = client.messages.create(
                model=VALIDATION_MODEL,
                max_tokens=MAX_TOKENS,
                system=_SYSTEM,
                messages=[{'role': 'user', 'content': prompt}],
            )
            elapsed = time.time() - t0
            raw = response.content[0].text.strip()

            v = _parse_json_response(raw)
            if v is None:
                print(f'PARSE ERROR (raw: {raw[:120]!r})')
                continue

            rel = v.get('reliability', '?')
            n_flagged = len(v.get('flagged_claims', []))
            rec = v.get('recommendation', '?')
            print(f'{rel} ({elapsed:.0f}s) — {n_flagged} flagged')
            print(f'     {v.get("confidence_note", "")}')
            print(f'     Recommendation: {rec}')
            for c in v.get('flagged_claims', []):
                print(f'     ⚠  [{c["risk"]}] {c["claim"][:80]}')
                print(f'          → {c["reason"][:100]}')

            # Write result to cache
            data['_validation'] = {**v,
                'validated_at': datetime.now(timezone.utc).isoformat(),
                'validated_by': VALIDATION_MODEL,
            }
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

        except Exception as e:
            print(f'ERROR: {e}')

        print()


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Validate BibCrit cache via Opus critic pass')
    parser.add_argument('--sample',      type=int,  metavar='N',  help='Validate N entries immediately (live API)')
    parser.add_argument('--tool',        type=str,                help='Only validate entries for this tool')
    parser.add_argument('--force',       action='store_true',     help='Re-validate already-validated entries')
    parser.add_argument('--submit-only', action='store_true',     help='Submit batch but do not wait for results')
    parser.add_argument('--poll-batch',  type=str,  metavar='ID', help='Poll an existing batch ID and write results')
    args = parser.parse_args()

    entries = _load_cache_files(tool_filter=args.tool)
    if not entries:
        print('No cache entries found.')
        return

    # Filter already-validated unless --force
    if not args.force:
        pending = [(p, d) for p, d in entries if '_validation' not in d]
    else:
        pending = entries

    print(f'Cache entries: {len(entries)} total, {len(pending)} pending validation')
    if args.tool:
        print(f'Tool filter: {args.tool}')

    if args.poll_batch:
        # We need the id_to_path map — rebuild from cache files
        id_to_path = {p.stem: p for p, _ in entries}
        _poll_and_write(args.poll_batch, id_to_path)
        return

    if args.sample:
        _print_sample(pending, args.sample)
        return

    batch_id, id_to_path = _submit_batch(pending, force=args.force)

    if args.submit_only:
        print(f'\nBatch submitted. Run later with:')
        print(f'  python scripts/validate_cache.py --poll-batch {batch_id}')
        return

    _poll_and_write(batch_id, id_to_path)


if __name__ == '__main__':
    main()
