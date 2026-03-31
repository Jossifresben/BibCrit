#!/usr/bin/env python3
"""Pre-cache all analyses so the repo ships with a full set of results.

Runs only items that are NOT already cached — safe to re-run at any time.

Usage:
    python scripts/precache_all.py              # everything missing
    python scripts/precache_all.py --type numerical
    python scripts/precache_all.py --type backtranslation
    python scripts/precache_all.py --dry-run    # show what would run
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
except ImportError:
    pass

# ── What to cache ────────────────────────────────────────────────────────────

NUMERICAL_REFS = [
    'Genesis 5',
    'Genesis 11',
    'Numbers 35',
    '1 Kings 6',
    '2 Samuel 10',
]

# High-interest back-translation passages (messianic + textually rich)
BACKTRANS_REFS = [
    'Isaiah 7:14',
    'Isaiah 9:6',
    'Isaiah 53:1',
    'Psalm 2:7',
    'Psalm 22:16',
    'Deuteronomy 32:8',
    'Genesis 1:1',
    'Micah 5:2',
    'Zechariah 9:9',
    'Joel 3:1',
]

# Scribal books — all ten are already cached by the earlier batch run,
# but listed here so --type scribal can top them up if needed
SCRIBAL_BOOKS = [
    'Isaiah', 'Jeremiah', 'Psalms', 'Genesis', 'Deuteronomy',
    'Exodus', 'Proverbs', 'Job', 'Micah', 'Zechariah',
]

# Theological — featured books + passages from the UI chips
THEOLOGICAL_REFS = [
    # Books
    'Genesis', 'Isaiah', 'Psalms', 'Exodus',
    'Deuteronomy', 'Daniel', 'Job', 'Numbers',
    # Passages
    'Isaiah 7:14', 'Deuteronomy 32:8', 'Genesis 1:26', 'Exodus 24:10',
    'Proverbs 8:22', 'Isaiah 6:3', 'Genesis 18:1', 'Exodus 4:24',
    'Isaiah 53:10', 'Psalm 110:1',
]

# Patristic — featured passages from the UI chips
PATRISTIC_REFS = [
    'Isaiah 7:14', 'Psalm 22:1', 'Isaiah 53:12', 'Genesis 1:1',
    'Psalm 110:1', 'Isaiah 9:6', 'Micah 5:2', 'Zechariah 12:10',
    'Psalm 2:7', 'Isaiah 40:3', 'Deuteronomy 6:4', 'Proverbs 8:22',
]


def main() -> None:
    parser = argparse.ArgumentParser(description='Pre-cache BibCrit analyses')
    parser.add_argument('--type', choices=['numerical', 'backtranslation', 'scribal', 'theological', 'patristic'],
                        help='Only run this analysis type (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be cached without calling the API')
    args = parser.parse_args()

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

    from biblical_core.claude_pipeline import (
        ClaudePipeline, SCRIBAL_MODEL, NUMERICAL_MODEL,
        THEOLOGICAL_MODEL, PATRISTIC_MODEL,
        _SCRIBAL_SAMPLE_REFS,
    )
    from biblical_core.corpus import BiblicalCorpus

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key and not args.dry_run:
        sys.exit('ERROR: ANTHROPIC_API_KEY not set.')

    corpus = BiblicalCorpus()
    corpus.set_data_dir(data_dir)
    try:
        corpus.load_all()
    except Exception as e:
        print(f'Warning: corpus load failed ({e}) — back-translation will use Claude knowledge only')

    pipeline = ClaudePipeline(
        data_dir=data_dir,
        api_key=api_key,
        cap_usd=float(os.environ.get('BIBCRIT_API_CAP_USD', '50.0')),  # raised cap for batch
        supabase_url=os.environ.get('SUPABASE_URL', ''),
        supabase_key=os.environ.get('SUPABASE_KEY', ''),
    )

    _BACKTRANS_PROMPT    = 'v1'
    _NUMERICAL_PROMPT    = 'v1'
    _SCRIBAL_PROMPT      = 'v1'
    _THEOLOGICAL_PROMPT  = 'v1'
    _PATRISTIC_PROMPT    = 'v1'

    total = skipped = ran = errors = 0

    def run_numerical():
        nonlocal total, skipped, ran, errors
        for ref in NUMERICAL_REFS:
            total += 1
            cached = pipeline.get_cached(ref, 'numerical', _NUMERICAL_PROMPT, NUMERICAL_MODEL)
            if cached:
                print(f'  ⚡ SKIP  numerical  {ref}  (cached)')
                skipped += 1
                continue
            if args.dry_run:
                print(f'  ○ WOULD RUN  numerical  {ref}')
                continue
            print(f'  → RUN   numerical  {ref} …', end='', flush=True)
            t0 = time.time()
            result = pipeline.analyze_numerical(ref)
            elapsed = time.time() - t0
            if result.get('error'):
                print(f' ❌  {result["error"]}')
                errors += 1
            else:
                print(f' ✓  {elapsed:.0f}s')
                ran += 1

    def run_backtranslation():
        nonlocal total, skipped, ran, errors
        for ref in BACKTRANS_REFS:
            total += 1
            cached = pipeline.get_cached(ref, 'backtranslation', _BACKTRANS_PROMPT, 'claude-sonnet-4-5-20250929')
            if cached:
                print(f'  ⚡ SKIP  backtranslation  {ref}  (cached)')
                skipped += 1
                continue
            if args.dry_run:
                print(f'  ○ WOULD RUN  backtranslation  {ref}')
                continue
            # Get LXX text from corpus
            lxx_text = ''
            try:
                words = corpus.get_verse_words(ref, 'LXX')
                if words:
                    lxx_text = ' '.join(w.word_text for w in words)
            except Exception:
                pass

            print(f'  → RUN   backtranslation  {ref} …', end='', flush=True)
            t0 = time.time()
            result = pipeline.analyze_backtranslation(ref, lxx_text, '')
            elapsed = time.time() - t0
            if result.get('error'):
                print(f' ❌  {result["error"]}')
                errors += 1
            else:
                print(f' ✓  {elapsed:.0f}s')
                ran += 1

    def run_scribal():
        nonlocal total, skipped, ran, errors
        for book in SCRIBAL_BOOKS:
            total += 1
            cached = pipeline.get_cached(book, 'scribal', _SCRIBAL_PROMPT, SCRIBAL_MODEL)
            if cached:
                print(f'  ⚡ SKIP  scribal  {book}  (cached)')
                skipped += 1
                continue
            if args.dry_run:
                print(f'  ○ WOULD RUN  scribal  {book}')
                continue
            # Build sample passages
            refs = _SCRIBAL_SAMPLE_REFS.get(book, [])
            lines = []
            for r in refs:
                try:
                    mt  = corpus.get_verse_words(r, 'MT')
                    lxx = corpus.get_verse_words(r, 'LXX')
                    mt_t  = ' '.join(w.word_text for w in mt)  if mt  else '(not found)'
                    lxx_t = ' '.join(w.word_text for w in lxx) if lxx else '(not found)'
                    lines.append(f'{r}:\n  MT:  {mt_t}\n  LXX: {lxx_t}')
                except Exception:
                    pass
            sample = '\n\n'.join(lines) or f'(Profile {book} from training knowledge)'

            print(f'  → RUN   scribal  {book} …', end='', flush=True)
            t0 = time.time()
            result = pipeline.analyze_scribal(book, sample)
            elapsed = time.time() - t0
            if result.get('error'):
                print(f' ❌  {result["error"]}')
                errors += 1
            else:
                print(f' ✓  {elapsed:.0f}s')
                ran += 1

    def run_theological():
        nonlocal total, skipped, ran, errors
        for ref in THEOLOGICAL_REFS:
            total += 1
            cached = pipeline.get_cached(ref, 'theological', _THEOLOGICAL_PROMPT, THEOLOGICAL_MODEL)
            if cached:
                print(f'  ⚡ SKIP  theological  {ref}  (cached)')
                skipped += 1
                continue
            if args.dry_run:
                print(f'  ○ WOULD RUN  theological  {ref}')
                continue
            print(f'  → RUN   theological  {ref} …', end='', flush=True)
            t0 = time.time()
            result = pipeline.analyze_theological(ref)
            elapsed = time.time() - t0
            if result.get('error'):
                print(f' ❌  {result["error"]}')
                errors += 1
            else:
                print(f' ✓  {elapsed:.0f}s')
                ran += 1

    def run_patristic():
        nonlocal total, skipped, ran, errors
        for ref in PATRISTIC_REFS:
            total += 1
            cached = pipeline.get_cached(ref, 'patristic', _PATRISTIC_PROMPT, PATRISTIC_MODEL)
            if cached:
                print(f'  ⚡ SKIP  patristic  {ref}  (cached)')
                skipped += 1
                continue
            if args.dry_run:
                print(f'  ○ WOULD RUN  patristic  {ref}')
                continue
            print(f'  → RUN   patristic  {ref} …', end='', flush=True)
            t0 = time.time()
            result = pipeline.analyze_patristic(ref)
            elapsed = time.time() - t0
            if result.get('error'):
                print(f' ❌  {result["error"]}')
                errors += 1
            else:
                print(f' ✓  {elapsed:.0f}s')
                ran += 1

    run_type = args.type
    print(f'\nPre-cache run — type={run_type or "all"}  dry_run={args.dry_run}\n')

    if not run_type or run_type == 'numerical':
        print('── Numerical ───────────────────────────────────')
        run_numerical()

    if not run_type or run_type == 'backtranslation':
        print('\n── Back-translation ────────────────────────────')
        run_backtranslation()

    if not run_type or run_type == 'scribal':
        print('\n── Scribal ─────────────────────────────────────')
        run_scribal()

    if not run_type or run_type == 'theological':
        print('\n── Theological ─────────────────────────────────')
        run_theological()

    if not run_type or run_type == 'patristic':
        print('\n── Patristic ───────────────────────────────────')
        run_patristic()

    print(f'\n{"DRY RUN — " if args.dry_run else ""}Done.  '
          f'Total={total}  Ran={ran}  Skipped={skipped}  Errors={errors}')
    if errors:
        sys.exit(1)


if __name__ == '__main__':
    main()
