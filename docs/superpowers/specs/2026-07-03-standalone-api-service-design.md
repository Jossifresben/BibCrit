# BibCrit Standalone API Service — Design

**Date:** 2026-07-03
**Author:** Jossi Fresco (design approved interactively)
**Repo:** `bibcrit-private` (github.com/Jossifresben/bibcrit-private) — the old public repo stays untouched
**Builds on:** `docs/superpowers/specs/2026-07-01-open-api-v1-design.md` (versioning, API keys, rate limiting — merged to main as commits dcd0b52…bb4c23d)

---

## Goal

Ship the BibCrit API as a **standalone, separately deployed, key-gated service** (eventually `api.bibcrit.app`) — the monetizable product, in association with Elia Fiore — while the website (`bibcrit.app`) stays free and behaves exactly as it does in production today.

## Decisions already made (interactively, do not re-litigate)

1. **Website free, API monetized.** The site keeps its own keyless, same-origin analysis streams; the standalone API requires keys.
2. **No new repo.** Collaborators may see the whole codebase, so the API lives in `bibcrit-private` alongside the website — one shared core, two deployed services. A separate repo was rejected: it would force duplicating (or extracting into a third package) the 2,500-line pipeline and 151 MB corpus that both services need identically.
3. **Website-as-API-client rejected.** The site keeps calling its own server, not the API service.

## The bug this design also fixes (critical context)

The Open API v1 branch (already merged to `main` in the private repo, **not deployed anywhere**) hard-wired `@require_api_key` onto every analysis-stream route. But the website's own tool pages call those same routes via the browser's `EventSource`, which **cannot send custom headers** — so every "Analyze" button would receive 401 if that main were deployed. Production is safe only because bibcrit.app still deploys from the old public repo, which never received this code. This design resolves the conflict structurally: enforcement becomes per-service configuration instead of per-route hardcoding. **Nothing may be deployed from `bibcrit-private` until this design is implemented.**

---

## Design

### 1. One repo, two Flask apps via a shared factory

Refactor `app.py`'s `create_app()` into `create_app(mode: str)` with two modes:

| | `web` (bibcrit.app) | `api` (api.bibcrit.app) |
|---|---|---|
| Entry point | `app.py`: `app = create_app('web')` — **gunicorn command unchanged** (`gunicorn app:app`) | `api_app.py` (new, ~3 lines): `app = create_app('api')` |
| API blueprints (textual, critical, discovery, literary, targum, nt_text, stl, lxx_ms, research, api_v1) | ✓ | ✓ |
| Pages blueprint (all HTML routes) | ✓ | ✗ (404) |
| Admin blueprint (dash + flag endpoint) | ✓ | ✗ (absent — can never appear on the paid API) |
| SEO routes (robots.txt, sitemap.xml, llms.txt) | ✓ | ✗ |
| `/health`, `/api/docs`, `/api/v1/openapi.json` | ✓ | ✓ |
| Limiter, CORS hook, 429 handler, i18n context processor, `before_request _init` | ✓ | ✓ |
| `REQUIRE_API_KEYS` config | `False` (explicit) | `True` |
| `TIER1_RATE_LIMIT` config | `'60/hour'` (per IP) | `'20/hour'` (per key) |

The i18n context processor and template folder stay in both modes because `/api/docs` (`templates/api_docs.html`) extends `base.html`.

The current module-level `@app.route` registrations in `app.py` (robots/sitemap/llms) and the module-level CORS/429/context-processor hooks move inside the factory (SEO into web mode only; the rest into both). `app.py` continues to expose a module-level `app` so Render's existing start command and the existing test fixture keep working unmodified.

### 2. Blueprint split: pages out, API stays

- New `blueprints/pages.py` (`pages_bp`): all 19 page routes move there **verbatim** — index `/`, the 15 tool pages, `/discovery`, `/guide`, `/paper` (`/health` stays with the API side of `research.py`, since both services serve it). Each is a 3–6-line `render_template` call; no logic changes.
- Existing blueprint files keep only their API routes (plus the helper functions those routes use) and become pure API modules.
- `/api/admin/discovery/flag` (POST) moves from `discovery.py` to `admin.py`, consolidating the entire admin surface into the website-only blueprint.
- **Verified safe:** no template or Python code calls `url_for()` on any page endpoint (only `url_for('static', …)` exists), and nav links are hard-coded paths — so endpoint renames from the move (`textual.divergence` → `pages.divergence`) break nothing, and no URL changes.

### 3. Per-service key enforcement (the EventSource fix)

`biblical_core/api_auth.py`'s `require_api_key` gains one check at the top of the wrapper:

```python
if not current_app.config.get('REQUIRE_API_KEYS', True):
    return view(*args, **kwargs)
```

- **Default `True` = fail-closed.** A deployment that forgets to configure gets key enforcement (visible 401s), never silent free Claude access. Only the web factory explicitly opts out.
- Website result: `EventSource('/api/divergence/stream?...')` works keylessly again, same-origin, exactly like production today.
- API service result: identical route code returns 401 without a valid `X-API-Key`, as the Open API v1 design intended.
- Accepted tradeoff (explicit): anyone can still use the free website instead of paying for the API. That is the chosen model — the paid API sells programmatic access, keys, stable versioning, and docs; the website remains the free demo. The website's protection is its IP rate limit plus the existing `$BIBCRIT_API_CAP_USD` monthly circuit breaker.

### 4. Per-service Tier-1 rate limits

The hard-coded `'20/hour'` on Tier-1 routes becomes a config lookup — flask-limiter accepts a callable: `@limiter.limit(lambda: current_app.config['TIER1_RATE_LIMIT'], key_func=api_key_or_ip)`.

- Web: `60/hour` per IP (keyless visitors fall through `api_key_or_ip` to IP). Rationale: 20/hour would 429 a student clicking through cached featured passages; 60/hour still caps worst-case spend far below the monthly circuit breaker.
- API: `20/hour` per key (unchanged from the Open API v1 design and its cost math).
- Tier-0 (`60/minute;1000/day`) and vote-write (`20/hour`) limits stay identical in both modes and stay hard-coded.
- In-memory limiter storage remains valid: each service is its own single-gunicorn-worker process with independent counters. The existing "must move to Redis if `--workers` > 1" caveat in `rate_limit.py` now applies to each service separately.

### 5. Deployment

`render.yaml` gains a second service:

```yaml
  - type: web
    name: bibcrit-api
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn api_app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180
    envVars: (same keys as the web service: PYTHON_VERSION, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_KEY, BIBCRIT_API_CAP_USD)
```

Committing this is inert — nothing deploys until Render is connected to `bibcrit-private` (a dashboard step the owner performs separately, deliberately out of scope per prior instruction). Both services will share the same Supabase project (`analysis_cache`, `analysis_cache_es`, `api_keys`, `budget`) and the same monthly spend cap, which therefore covers web + API combined.

Deferred to launch time (tracked, not in this implementation): connecting Render to the private repo, creating the `bibcrit-api` service, pointing `api.bibcrit.app` DNS, and updating `_OPENAPI_SPEC['servers']` to list `https://api.bibcrit.app` first.

### 6. Testing

New fixture in `tests/test_integration.py`: `api_client` — builds `create_app('api')` with the same isolated tmp-path setup as the existing `client` (which remains web mode).

Required coverage:
- **The regression that would have caught the EventSource bug:** web `client`, keyless GET on a Tier-1 stream route → **not** 401 (reaches the route body).
- Same route on `api_client`, keyless → 401; with mocked-valid key (`authed_client`-style bypass) → passes through.
- **The existing Tier-1 401 tests move** from the web `client` to `api_client` (on the web app they now correctly fail, since enforcement is off there).
- Page routes (`/`, `/divergence`, `/discovery`) → 404 on `api_client`; 200 on web `client`.
- Admin routes (`/bibcrit-admin-dash`, `/api/admin/discovery/flag`) → 404 on `api_client`.
- `/health`, `/api/docs`, `/api/v1/openapi.json` → 200 on both.
- Tier-1 limit configurability: web app's limit is `60/hour`, api app's is `20/hour` (assert via config, plus one behavioral 429 test on either app).
- Full existing suite still passes in web mode (the only intended diffs are the moved 401 tests and the flipped keyless-stream expectation).

### Out of scope (explicit)

- Billing/payments for keys (keys remain free; monetization mechanics are a business decision for later).
- Any change to the old public repo or to current production.
- Render dashboard wiring / DNS (launch-time runbook, separate from code).
- Redis / multi-worker scaling.
- Extracting `biblical_core` into a package (rejected with the separate-repo approach).
