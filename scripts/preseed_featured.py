#!/usr/bin/env python3
"""Pre-seed BibCrit disk cache + Supabase for every featured passage.

Hits each SSE endpoint over HTTP so the full pipeline runs (cache write to
disk + Supabase happens automatically).  Safe to re-run: cache hits return
in < 1 s without calling Claude.

Usage:
    python scripts/preseed_featured.py              # seed everything
    python scripts/preseed_featured.py --tool source
    python scripts/preseed_featured.py --dry-run

Estimated time (first run, no cache): ~40-50 min total.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("requests not installed — run: pip install requests")

BASE = "http://localhost:5001"

# ── Endpoint map (tool name → URL path segment) ─────────────────────────────
# Tools that use a hyphen in the URL rather than underscore:
ENDPOINT_OVERRIDES = {
    "nt_ot": "nt-ot",
}

# ── Featured passages ────────────────────────────────────────────────────────
# (tool, ref)  — tool must match a key in ENDPOINT_OVERRIDES or map directly
# to /api/{tool}/stream.  Ordered roughly by expected Claude time (fast → slow)
# so the script shows early progress quickly.

PASSAGES: list[tuple[str, str]] = [
    # ── DSS (missing: 4) ──────────────────────────────────────────────────────
    ("dss",             "Isaiah 7:14"),
    ("dss",             "Deuteronomy 32:8"),
    ("dss",             "Isaiah 53:11"),
    ("dss",             "Psalm 22:17"),

    # ── BACKTRANSLATION (missing: 3) ─────────────────────────────────────────
    ("backtranslation", "Isaiah 53:7"),
    ("backtranslation", "Psalm 2:7"),
    ("backtranslation", "Genesis 3:15"),

    # ── NUMERICAL (missing: 3) ────────────────────────────────────────────────
    ("numerical",       "Genesis 11"),
    ("numerical",       "Numbers 35"),
    ("numerical",       "1 Kings 6"),

    # ── THEOLOGICAL (missing: 1) ──────────────────────────────────────────────
    ("theological",     "Numbers"),

    # ── NT USE OF OT (new tool — all 4 featured passages) ────────────────────
    ("nt_ot",           "Matthew 1:23"),
    ("nt_ot",           "Hebrews 1:6"),
    ("nt_ot",           "Romans 15:12"),
    ("nt_ot",           "Acts 15:17"),

    # ── CHIASM (new tool — all 4 featured passages) ───────────────────────────
    ("chiasm",          "Amos 5:1-17"),
    ("chiasm",          "Genesis 1:1-2:3"),
    ("chiasm",          "Ruth 1:1-22"),
    ("chiasm",          "Psalm 136"),

    # ── SOURCE CRITICISM (new tool — all 4 featured passages) ────────────────
    ("source",          "Genesis 1:1-2:25"),
    ("source",          "Genesis 6:1-8"),
    ("source",          "Exodus 19:1-20:21"),
    ("source",          "Genesis 37"),

    # ── PATRISTIC (all 12 featured passages; Psalm 22:1 → 110:1) ─────────────
    ("patristic",       "Psalm 110:1"),
    ("patristic",       "Isaiah 7:14"),
    ("patristic",       "Isaiah 53:12"),
    ("patristic",       "Genesis 1:1"),
    ("patristic",       "Isaiah 9:6"),
    ("patristic",       "Micah 5:2"),
    ("patristic",       "Zechariah 12:10"),
    ("patristic",       "Psalm 2:7"),
    ("patristic",       "Isaiah 40:3"),
    ("patristic",       "Deuteronomy 6:4"),
    ("patristic",       "Proverbs 8:22"),
    ("patristic",       "Genesis 1:26"),
]


def stream_passage(tool: str, ref: str, timeout: int = 240) -> tuple[bool, str, float]:
    """
    Hit the SSE endpoint, consume the full stream.

    Returns (success, status_msg, elapsed_seconds).
    success=True even on a cache hit; False only on HTTP error or exception.
    """
    path = ENDPOINT_OVERRIDES.get(tool, tool)
    url  = f"{BASE}/api/{path}/stream"
    t0   = time.time()

    try:
        resp = requests.get(
            url,
            params={"ref": ref, "lang": "en"},
            stream=True,
            timeout=timeout,
        )
        resp.raise_for_status()

        last_event: dict = {}
        cached = False
        for raw in resp.iter_lines():
            if not raw:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")
            if not raw.startswith("data:"):
                continue
            try:
                event = json.loads(raw[5:].strip())
            except json.JSONDecodeError:
                continue

            etype = event.get("type")
            if etype == "step":
                msg = event.get("msg", "")
                if "cache" in msg.lower() and ("found" in msg.lower() or "⚡" in msg):
                    cached = True
            elif etype == "done":
                last_event = event
            elif etype == "error":
                elapsed = time.time() - t0
                return False, f"API error: {event.get('msg', '?')}", elapsed

        elapsed = time.time() - t0
        if last_event:
            tag = " (cached)" if cached else f" ({elapsed:.0f}s)"
            return True, f"✓{tag}", elapsed
        return False, "✗ stream ended without done event", elapsed

    except requests.exceptions.ConnectionError:
        elapsed = time.time() - t0
        return False, "✗ connection refused — is the server running on port 5001?", elapsed
    except requests.exceptions.Timeout:
        elapsed = time.time() - t0
        return False, f"✗ timed out after {timeout}s", elapsed
    except Exception as exc:
        elapsed = time.time() - t0
        return False, f"✗ {exc}", elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tool",    help="Only seed passages for this tool")
    parser.add_argument("--dry-run", action="store_true", help="Print what would run, don't call the server")
    args = parser.parse_args()

    passages = PASSAGES
    if args.tool:
        passages = [(t, r) for t, r in passages if t == args.tool]
        if not passages:
            sys.exit(f"No passages found for tool '{args.tool}'")

    total     = len(passages)
    passed    = 0
    failed    = 0
    run_start = time.time()

    print(f"\nBibCrit featured-passage pre-seeder")
    print(f"{'─' * 50}")
    print(f"Passages to seed : {total}")
    print(f"Server           : {BASE}")
    if args.dry_run:
        print("Mode             : DRY RUN\n")
    else:
        print()

    col_w = max(len(r) for _, r in passages) + 2

    for i, (tool, ref) in enumerate(passages, 1):
        label = f"[{i:02d}/{total}] {tool:<18} {ref:<{col_w}}"
        print(label, end="", flush=True)

        if args.dry_run:
            print("  (skipped)")
            continue

        ok, msg, elapsed = stream_passage(tool, ref)
        print(f"  {msg}")
        if ok:
            passed += 1
        else:
            failed += 1

    total_elapsed = time.time() - run_start

    if not args.dry_run:
        print(f"\n{'─' * 50}")
        print(f"Passed : {passed}/{total}")
        if failed:
            print(f"Failed : {failed}/{total}  ← re-run with --tool <name> to retry")
        print(f"Total  : {total_elapsed / 60:.1f} min")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
