#!/usr/bin/env python3
"""Translate all featured-passage EN caches to Spanish and store in analysis_cache_es."""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Passage/book lists (mirrors precache_all.py) ──────────────────────────────

NUMERICAL_REFS = [
    'Genesis 5', 'Genesis 11', '1 Kings 6', '1 Kings 7', 'Ezekiel 40',
    'Numbers 1', 'Numbers 26', '2 Samuel 24', '1 Chronicles 21', 'Judges 20',
    '2 Samuel 10', '1 Samuel 6:19', '2 Chronicles 13', 'Exodus 12:40',
    'Genesis 15:13', '1 Kings 6:1', 'Leviticus 25', 'Daniel 9',
    '1 Kings 14', '2 Kings 15', '2 Chronicles 36', 'Ezra 2', 'Nehemiah 7',
    'Numbers 35',
]

BACKTRANS_REFS = [
    'Exodus 3:14', 'Isaiah 53:7', 'Psalm 2:7', 'Genesis 3:15',
    'Isaiah 7:14', 'Isaiah 9:6', 'Isaiah 53:1', 'Deuteronomy 32:8',
    'Genesis 1:1', 'Micah 5:2', 'Zechariah 9:9', 'Joel 3:1',
]

DSS_REFS = [
    'Isaiah 7:14', 'Deuteronomy 32:8', 'Isaiah 53:11', 'Psalm 22:17',
]

SCRIBAL_BOOKS = [
    'Isaiah', 'Jeremiah', 'Psalms', 'Genesis', 'Deuteronomy',
    'Exodus', 'Proverbs', 'Job', 'Micah', 'Zechariah',
]

THEOLOGICAL_REFS = [
    'Genesis', 'Isaiah', 'Psalms', 'Exodus', 'Deuteronomy', 'Daniel', 'Job',
    'Isaiah 7:14', 'Deuteronomy 32:8', 'Genesis 1:26', 'Exodus 24:10',
    'Proverbs 8:22', 'Isaiah 6:3', 'Genesis 18:1', 'Exodus 4:24',
    'Isaiah 53:10', 'Psalm 110:1',
]

PATRISTIC_REFS = [
    'Isaiah 7:14', 'Genesis 1:26', 'Isaiah 53:12', 'Genesis 1:1',
    'Psalm 110:1', 'Isaiah 9:6', 'Micah 5:2', 'Zechariah 12:10',
    'Psalm 2:7', 'Isaiah 40:3', 'Deuteronomy 6:4', 'Proverbs 8:22',
]

GENEALOGY_BOOKS = [
    'Isaiah', 'Psalms', 'Genesis', 'Jeremiah',
    'Deuteronomy', 'Daniel', 'Ezekiel', 'Numbers',
]

DIVERGENCE_REFS = [
    'Isaiah 7:14', 'Genesis 1:1', 'Psalm 22:1', 'Deuteronomy 32:8',
]

# tool → (refs, prompt_version, model_constant_name)
TOOL_CONFIGS = [
    ('numerical',      NUMERICAL_REFS,   'v3', 'NUMERICAL_MODEL'),
    ('backtranslation',BACKTRANS_REFS,   'v1', 'DIVERGENCE_MODEL'),
    ('dss',            DSS_REFS,         'v5', 'DSS_MODEL'),
    ('scribal',        SCRIBAL_BOOKS,    'v1', 'SCRIBAL_MODEL'),
    ('theological',    THEOLOGICAL_REFS, 'v1', 'THEOLOGICAL_MODEL'),
    ('patristic',      PATRISTIC_REFS,   'v3', 'PATRISTIC_MODEL'),
    ('genealogy',      GENEALOGY_BOOKS,  'v1', 'GENEALOGY_MODEL'),
    ('divergence',     DIVERGENCE_REFS,  'v2', 'DIVERGENCE_MODEL'),
]


def main() -> None:
    parser = argparse.ArgumentParser(description='Translate BibCrit EN caches to Spanish')
    parser.add_argument('--type', choices=[t for t, *_ in TOOL_CONFIGS],
                        help='Only translate this tool (default: all)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be translated without calling the API')
    args = parser.parse_args()

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

    from biblical_core.claude_pipeline import (
        ClaudePipeline,
        NUMERICAL_MODEL, DIVERGENCE_MODEL, DSS_MODEL, SCRIBAL_MODEL,
        THEOLOGICAL_MODEL, PATRISTIC_MODEL, GENEALOGY_MODEL,
    )

    MODEL_MAP = {
        'NUMERICAL_MODEL':   NUMERICAL_MODEL,
        'DIVERGENCE_MODEL':  DIVERGENCE_MODEL,
        'DSS_MODEL':         DSS_MODEL,
        'SCRIBAL_MODEL':     SCRIBAL_MODEL,
        'THEOLOGICAL_MODEL': THEOLOGICAL_MODEL,
        'PATRISTIC_MODEL':   PATRISTIC_MODEL,
        'GENEALOGY_MODEL':   GENEALOGY_MODEL,
    }

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key and not args.dry_run:
        sys.exit('ERROR: ANTHROPIC_API_KEY not set.')

    pipeline = ClaudePipeline(
        data_dir=data_dir,
        api_key=api_key,
        cap_usd=float(os.environ.get('BIBCRIT_API_CAP_USD', '50.0')),
        supabase_url=os.environ.get('SUPABASE_URL', ''),
        supabase_key=os.environ.get('SUPABASE_KEY', ''),
    )

    total = skipped = ran = errors = 0
    run_type = args.type
    print(f'\nSpanish translation run — type={run_type or "all"}  dry_run={args.dry_run}\n')

    for tool, refs, prompt_v, model_key in TOOL_CONFIGS:
        if run_type and run_type != tool:
            continue

        model = MODEL_MAP[model_key]
        print(f'── {tool.capitalize()} ───────────────────────────────────')

        for ref in refs:
            total += 1

            # Skip if ES cache already exists
            cached_es = pipeline.get_cached_es(ref, tool, prompt_v, model)
            if cached_es:
                print(f'  ⚡ SKIP  {tool:15}  {ref}  (es cached)')
                skipped += 1
                continue

            # Get EN cache — skip if not yet seeded
            en_data = pipeline.get_cached(ref, tool, prompt_v, model)
            if not en_data:
                print(f'  ⚠ NO EN  {tool:15}  {ref}  (en cache missing — run precache_all.py first)')
                skipped += 1
                continue

            if args.dry_run:
                print(f'  ○ WOULD TRANSLATE  {tool:15}  {ref}')
                continue

            print(f'  → {tool:15}  {ref} …', end='', flush=True)
            t0 = time.time()
            translated = pipeline.translate_to_spanish(en_data, tool)
            elapsed = time.time() - t0

            if translated.get('error'):
                print(f' ❌  {translated["error"]}')
                errors += 1
            else:
                pipeline.save_cache_es(ref, tool, prompt_v, model, translated)
                print(f' ✓  {elapsed:.0f}s')
                ran += 1

        print()

    print(f'{"DRY RUN — " if args.dry_run else ""}Done.  '
          f'Total={total}  Ran={ran}  Skipped={skipped}  Errors={errors}')


if __name__ == '__main__':
    main()
