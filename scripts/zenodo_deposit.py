#!/usr/bin/env python3
"""Create / inspect / publish a Zenodo dataset deposit for the BibCrit cache bundle.

Reads ZENODO_TOKEN from .env (git-ignored). Production Zenodo by default;
pass --sandbox to use sandbox.zenodo.org.

Commands:
    create   Create a draft, upload bundle files, set metadata from .zenodo.json.
             Prints the deposition id, reserved DOI, concept DOI (if available),
             and the review URL. Does NOT publish.
    show ID  Print current state of deposition ID (DOIs, links, files).
    publish ID
             Publish deposition ID (IRREVERSIBLE). Prints the final DOIs.

Usage:
    python scripts/zenodo_deposit.py create [BUNDLE_DIR]
    python scripts/zenodo_deposit.py show 1234567
    python scripts/zenodo_deposit.py publish 1234567
"""
from __future__ import annotations
import json, os, sys
import requests

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, ".env"))
except ImportError:
    pass

SANDBOX = "--sandbox" in sys.argv
if SANDBOX:
    sys.argv.remove("--sandbox")
BASE = "https://sandbox.zenodo.org" if SANDBOX else "https://zenodo.org"
TOKEN = os.environ.get("ZENODO_TOKEN", "")
if not TOKEN:
    sys.exit("ERROR: ZENODO_TOKEN not set in .env or environment.")

S = requests.Session()
S.params = {"access_token": TOKEN}
H = {"Content-Type": "application/json"}

DEFAULT_BUNDLE = os.path.expanduser("~/Desktop/bibcrit_cache_dataset")
UPLOAD_FILES = ["bibcrit_analysis_cache.jsonl", "dataset_stats.json",
                "README.md", "LICENSE"]


def _dois(dep: dict) -> dict:
    md = dep.get("metadata", {})
    return {
        "deposition_id": dep.get("id"),
        "reserved_version_doi": (md.get("prereserve_doi") or {}).get("doi") or dep.get("doi"),
        "concept_doi": dep.get("conceptdoi"),
        "review_url": (dep.get("links") or {}).get("html"),
        "state": dep.get("state"),
        "submitted": dep.get("submitted"),
    }


def create(bundle_dir: str):
    md_path = os.path.join(bundle_dir, ".zenodo.json")
    meta = json.load(open(md_path, encoding="utf-8"))
    # classic deposit API expects license id lowercased
    if isinstance(meta.get("license"), str):
        meta["license"] = meta["license"].lower()

    print(f"[{BASE}] creating draft deposition ...")
    r = S.post(f"{BASE}/api/deposit/depositions", json={}, headers=H)
    r.raise_for_status()
    dep = r.json()
    dep_id = dep["id"]
    bucket = dep["links"]["bucket"]
    print(f"  draft id = {dep_id}")

    for fn in UPLOAD_FILES:
        p = os.path.join(bundle_dir, fn)
        if not os.path.exists(p):
            print(f"  SKIP (missing): {fn}")
            continue
        with open(p, "rb") as fh:
            up = S.put(f"{bucket}/{fn}", data=fh)
        up.raise_for_status()
        print(f"  uploaded {fn} ({os.path.getsize(p)} bytes)")

    r2 = S.put(f"{BASE}/api/deposit/depositions/{dep_id}",
               json={"metadata": meta}, headers=H)
    r2.raise_for_status()
    dep = r2.json()
    info = _dois(dep)
    print(json.dumps(info, indent=2))
    print("\nNext: review at the URL above, then either publish in the web UI or run:")
    print(f"    python scripts/zenodo_deposit.py publish {dep_id}"
          + (" --sandbox" if SANDBOX else ""))
    return info


def show(dep_id: str):
    r = S.get(f"{BASE}/api/deposit/depositions/{dep_id}")
    r.raise_for_status()
    print(json.dumps(_dois(r.json()), indent=2))


def publish(dep_id: str):
    r = S.post(f"{BASE}/api/deposit/depositions/{dep_id}/actions/publish")
    r.raise_for_status()
    dep = r.json()
    info = _dois(dep)
    print("PUBLISHED.")
    print(json.dumps(info, indent=2))
    print("\nUse the concept_doi (resolves to latest version) in the paper.")
    return info


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "create"
    if cmd == "create":
        create(sys.argv[2] if len(sys.argv) > 2 else DEFAULT_BUNDLE)
    elif cmd == "show":
        show(sys.argv[2])
    elif cmd == "publish":
        publish(sys.argv[2])
    else:
        sys.exit(f"unknown command: {cmd}")
