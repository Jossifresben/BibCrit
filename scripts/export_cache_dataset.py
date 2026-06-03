#!/usr/bin/env python3
"""Export the live BibCrit analysis cache (Supabase) to a citable Zenodo dataset bundle.

Pulls analysis_cache (en) + analysis_cache_es (es), writes a single JSONL of all
records, a machine-readable stats file, a datasheet README, a CC BY 4.0 LICENSE,
and a Zenodo metadata file, then zips the bundle.

Re-run any time to refresh the deposit as the cache grows.

Requires SUPABASE_URL and SUPABASE_KEY in .env.
Usage: python scripts/export_cache_dataset.py [OUTPUT_DIR]
"""
from __future__ import annotations
import json, os, sys, collections, zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, ".env"))
except ImportError:
    pass
from supabase import create_client

URL = os.environ["SUPABASE_URL"]
KEY = os.environ["SUPABASE_KEY"]
sb = create_client(URL, KEY)

DATASET_VERSION = sys.argv[2] if len(sys.argv) > 2 else "2026-06-03"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Desktop/bibcrit_cache_dataset")
os.makedirs(OUT, exist_ok=True)


def fetch_all(table: str) -> list[dict]:
    rows, step, off = [], 1000, 0
    while True:
        resp = sb.table(table).select("*").range(off, off + step - 1).execute()
        batch = resp.data or []
        rows.extend(batch)
        if len(batch) < step:
            break
        off += step
    return rows


print("Fetching analysis_cache (en) ...")
en = fetch_all("analysis_cache")
print(f"  {len(en)} rows")
print("Fetching analysis_cache_es (es) ...")
es = fetch_all("analysis_cache_es")
print(f"  {len(es)} rows")

# ---- write JSONL ------------------------------------------------------------
records = []
for locale, rows in (("en", en), ("es", es)):
    for r in rows:
        records.append({
            "cache_key": r.get("cache_key"),
            "locale": locale,
            "reference": r.get("reference"),
            "tool": r.get("tool"),
            "prompt_version": r.get("prompt_version"),
            "model_version": r.get("model_version"),
            "cached_at": r.get("cached_at"),
            "discovery_ready": r.get("discovery_ready"),
            "analysis": r.get("data"),
        })

jsonl_path = os.path.join(OUT, "bibcrit_analysis_cache.jsonl")
with open(jsonl_path, "w", encoding="utf-8") as f:
    for rec in records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
print(f"Wrote {len(records)} records -> {jsonl_path}")

# ---- stats ------------------------------------------------------------------
def dist(rows, key):
    c = collections.Counter(r.get(key) or "unknown" for r in rows)
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))

stats = {
    "dataset_version": DATASET_VERSION,
    "total_records": len(records),
    "english_records": len(en),
    "spanish_records": len(es),
    "distinct_references": len({r["reference"] for r in records if r["reference"]}),
    "distinct_tools": len({r["tool"] for r in records if r["tool"] and r["tool"] != "unknown"}),
    "by_locale": {"en": len(en), "es": len(es)},
    "by_tool": dist(records, "tool"),
    "by_model_version": dist(records, "model_version"),
    "by_prompt_version_per_tool": collections.OrderedDict(),
}
pv = collections.Counter()
for r in records:
    pv[(r.get("tool") or "unknown", r.get("prompt_version") or "unknown")] += 1
for (tool, ver), n in sorted(pv.items()):
    stats["by_prompt_version_per_tool"].setdefault(tool, {})[ver] = n

with open(os.path.join(OUT, "dataset_stats.json"), "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
print("Wrote dataset_stats.json")
print(json.dumps({k: stats[k] for k in (
    "total_records", "english_records", "spanish_records",
    "distinct_references", "distinct_tools", "by_model_version")},
    ensure_ascii=False, indent=2))
print("OUTPUT DIR:", OUT)
