# BibCrit Open API v1 — Design

**Date:** 2026-07-01
**Author:** Jossi Fresco (design drafted unattended by Claude per explicit request — see note below)
**Roadmap source:** `docs/superpowers/specs/2026-04-14-bibcrit-6month-roadmap-design.md`, Phase 3 infrastructure item "Full open API v1"

> **Process note:** this spec was produced in one unattended pass (brainstorm → design → spec) at the user's explicit request, skipping the normal one-question-at-a-time interactive checklist. Every non-obvious decision below is documented with its reasoning so it can be reviewed and overridden after the fact, the same way it would have been settled through dialogue.

---

## Context: what already exists (verified against the live repo, not the old roadmap doc)

The 2026-04-14 roadmap doc's wishlist for this item was "Versioned endpoints (`/api/v1/...`), API key management and rate limiting, Swagger/OpenAPI documentation at `/api/docs`." Re-checking the actual code (2026-07-01):

| Roadmap ask | Actual state |
|---|---|
| Swagger/OpenAPI docs at `/api/docs` | **Done.** `blueprints/research.py` has a full hand-written OpenAPI 3.0 spec (`_OPENAPI_SPEC`, ~30 documented paths across 6 tags) served at `/api/v1/openapi.json`, rendered as Swagger UI at `/api/docs` (`templates/api_docs.html`). |
| Versioned endpoints | **Not done.** The spec is served from a `/api/v1/` URL, but every path it *documents* is the bare, unversioned form (`/api/divergence/stream`, `/api/cache`, etc.). There is no `/api/v1/<anything>` route except the spec JSON itself. |
| API key management | **Not done.** Zero API-key infrastructure. The only existing auth is two internal single-shared-secret admin tokens (`ADMIN_TOKEN` for `/bibcrit-admin-dash`, `BIBCRIT_ADMIN_KEY` for the discovery-flag toggle) — neither is suited to public, multi-tenant, revocable key issuance. |
| Rate limiting | **Not done.** No `flask-limiter` (or anything else) in `requirements.txt`; no throttling anywhere, including on the SSE analysis-stream endpoints that trigger real Claude API spend on a cache miss. |

So the real remaining work is three things: **route versioning, API keys, rate limiting** — not a from-scratch API.

### Deployment facts that shape this design
- `render.yaml`: `gunicorn app:app --workers 1 --threads 4 --timeout 180` — **single worker process.** An in-memory rate-limit counter is safe (no cross-process drift) without adding Redis. This must be re-examined if `--workers` is ever raised above 1.
- Existing cost circuit breaker: `biblical_core/claude_pipeline.py` already tracks monthly spend (`get_budget()`/`record_spend()`) against `BIBCRIT_API_CAP_USD` (env, default `$20.0` per `render.yaml`) and blocks new paid analysis once the cap is hit (`claude_pipeline.py:811`). This is the **existing hard financial backstop** — this design layers a second, faster-acting throttle in front of it; it does not replace or duplicate the spend tracking itself.
- Supabase project `bbykuapqqlsqkriflysq` currently has exactly 4 tables (`analysis_cache`, `analysis_cache_es`, `budget`, `hypothesis_votes`), all RLS-enabled. No `api_keys`/`users` table exists. (Pre-existing advisor notes flag `analysis_cache_es` having a couple of `USING (true)` write policies — not this project's concern, but a pattern this design deliberately avoids for its own new table.)
- Model cost constants (`claude_pipeline.py`): `$5`/MTok in, `$25`/MTok out (currently Opus 4.7 across all 13 analysis tools). Used below to size the per-key rate limit against real dollars, not an arbitrary number.

---

## Approaches considered

### Approach A — Two-tier: keyless public reads (IP-throttled) + API-key-gated analysis streams (key-throttled), both layered on the existing $ cap. — **Recommended**
Free, cached/corpus/export/vote-read endpoints stay exactly as open as they are today (just IP-rate-limited against casual abuse); a key is required only for the SSE endpoints that can trigger a real Claude call on a cache miss.
- **Pros:** Matches BibCrit's established identity — "free, open access" is called out as a named differentiator in the roadmap's own gap analysis, and `/api/cache` already ships a `license`/`citation` field implying frictionless anonymous consumption is a deliberate feature. Zero registration friction for the roadmap's actual stated goal ("seminaries and journals embed BibCrit tool results directly" — a read/embed use case). Protects the one thing that actually costs money without gatekeeping the rest.
- **Cons:** Two code paths (keyless + keyed) instead of one uniform rule. Anonymous IP throttling on reads is coarser than per-key accounting (acceptable — reads are cheap, local, and not what threatens the budget).

### Approach B — Require a key for every endpoint, uniformly.
- **Pros:** One mental model; best usage attribution across the board; simplest to build a per-consumer dashboard later.
- **Cons:** Directly contradicts the project's stated "free, open access" differentiator; adds signup friction to the exact embed use case the roadmap wants to unlock; disproportionate — nearly all abuse risk concentrates in the LLM-calling endpoints, not the cached reads.

### Approach C — Ship versioned routes + IP-based rate limiting everywhere; defer API keys entirely.
- **Pros:** Fastest; already closes today's real gap (nothing is throttled at all right now, including the expensive endpoints); avoids building an issuance flow before any external consumer has asked for one.
- **Cons:** Doesn't satisfy the roadmap's explicit "API key management" bullet; no way to attribute or revoke a specific bad actor without IP-banning (weak against rotating IPs / NAT'd institutions); the extra cost of doing key issuance on top of Approach A's design is small once the tiering already exists.

**Decision: Approach A.** It satisfies all three roadmap asks, reuses the existing budget cap instead of duplicating cost-tracking, requires no new infrastructure (no Redis, no billing, no user accounts), and fits the confirmed single-worker deployment.

---

## Design

### 1. Route versioning — alias, don't break

Every existing `/api/...` route gets a second registration at `/api/v1/...` pointing at the **same view function** (Flask's `add_url_rule` supports multiple rules → one view). Nothing that works today changes behavior.

- New canonical form: `/api/v1/divergence/stream`, `/api/v1/cache`, `/api/v1/keys` (new), etc.
- Old bare form (`/api/divergence/stream`) keeps working, marked `"deprecated": true` in the OpenAPI spec with a one-line sunset note ("use `/api/v1/...` — this alias is kept for compatibility and is not scheduled for removal"). No forced migration, no breakage risk, since we don't actually know if any external consumer already depends on the bare paths.
- `_OPENAPI_SPEC['paths']` in `blueprints/research.py` is mechanically regenerated: every existing key gets a `/api/v1` prefix added as the primary entry; the original bare key is kept alongside it with `deprecated: true`. `info.version` bumps from `1.0.0` → `1.1.0` (the API's public shape changed: new auth requirement on some paths, new `/api/v1/keys` path).
- `/health` is explicitly excluded from versioning changes and from all rate limiting — monitoring must never be throttled or moved.
- **Out of scope:** `/bibcrit-admin-dash` and `/api/admin/discovery/flag` are internal maintainer-only routes, already protected by their own single-shared-secret tokens, and are not part of the public API surface (neither appears in `_OPENAPI_SPEC['paths']` today). This design does not touch them — no versioning, no key gating, no new rate limit.
- **Classification rule for any route not yet enumerated in `_OPENAPI_SPEC['paths']`:** a full grep of the blueprints turns up a few existing `/api/...` routes the current spec doesn't document — e.g. the bare (non-stream) `/api/divergence`, and tool-specific export routes beyond the documented `/api/divergence/export/*` (such as `/api/scribal/export/sbl`, `/api/numerical/export/sbl`). Classify each with one rule: **if it can trigger a Claude call, it's Tier 1; if it only reads/formats already-cached data (corpus lookups, exports, cache/discovery reads), it's Tier 0** — regardless of which tool it belongs to. Add it to the OpenAPI spec (it should have been documented already) as part of this work, versioned the same way as everything else.

### 2. API keys

**Format:** `bibcrit_live_<32 url-safe chars>` via `secrets.token_urlsafe`. The `bibcrit_live_` prefix exists so a leaked key is trivially greppable in logs/scanners (same idea as Stripe/GitHub token prefixes).

**Storage — new Supabase table `api_keys`:**
| column | type | notes |
|---|---|---|
| `id` | uuid, pk | |
| `key_hash` | text, unique, not null | `sha256(raw_key)` — the raw key is never stored |
| `key_prefix` | text | first 12 chars of the raw key, for display only (e.g. `bibcrit_live_ab12***`) |
| `owner_name` | text | |
| `owner_email` | text | |
| `created_at` | timestamptz, default now() | |
| `last_used_at` | timestamptz, nullable | |
| `revoked` | boolean, default false | |
| `requests_total` | bigint, default 0 | incremented on each authenticated call; cheap usage signal, no dashboard built for it yet |

RLS: **enabled, zero policies.** Only the Flask backend (holding the Supabase service-role key already in `.env` as `SUPABASE_KEY`) ever touches this table; default-deny is the correct posture here — this deliberately avoids the `USING (true)` permissive-write pattern the security advisor already flagged on an unrelated existing table.

**Issuance — `POST /api/v1/keys`:** body `{name, email}` → creates a row, returns `{api_key: "bibcrit_live_..."}` **once**. The response body is the only delivery mechanism (no email infra exists in this project and none is being added — YAGNI). Docs state plainly: "store this now; it cannot be shown again; request a new one if lost." No login, no dashboard, no rotation UI — if a key needs to be revoked, that's a manual `UPDATE api_keys SET revoked = true` the maintainer runs directly (matches the actual scale of a solo-maintained project; a self-service revoke UI is not built).

**Presentation:** `X-API-Key` header, not a query parameter. This diverges from the existing internal admin-token convention (`?token=...`), deliberately: those are typed once by the maintainer, but third-party API consumers' proxies/logs are outside BibCrit's control, so a header avoids the key leaking into access logs, browser history, or Referer headers.

**Validation:** a `require_api_key` decorator — hash the incoming header, look up `api_keys` by `key_hash`, reject `revoked` or missing keys with `401` (not `403`; this is "you're unauthenticated," not "you're forbidden," and the error body links to `POST /api/v1/keys` so the DX is self-serve-discoverable) — bump `last_used_at` and `requests_total` on success.

### 3. Rate limiting

**Library:** `flask-limiter`, `storage_uri="memory://"` set explicitly (not left as an implicit default) with a code comment tying that choice to the confirmed single-worker `render.yaml` config, so a future change to `--workers N>1` doesn't silently break rate-limit accuracy without a matching comment update.

**Tier 0 — keyless, IP-based** (Corpus browser, Cache/Discovery reads, Export, vote-count reads, `/api/budget`):
- `60/minute, 1000/day` per IP — generous; these are cheap, local, corpus/cache lookups with no LLM cost.
- Vote **writes** (`POST /api/vote`, `POST /api/hypothesis/vote`) get a tighter `20/hour` per IP — no key required (keeps community engagement frictionless), just abuse-resistant against vote-stuffing.

**Tier 1 — API-key-gated** (the `*/stream` analysis endpoints — divergence, backtranslation, dss, genealogy, nt-ot, scribal, numerical, theological, patristic, chiasm, source, targum, nt-text — everything that can call Claude on a cache miss):
- `20/hour` per key.
- **Why 20/hour is defensible, not arbitrary:** worst-case single call ≈ 8192 output tokens × $25/MTok + a few-thousand-token prompt ≈ **~$0.22**. `20 × $0.22 ≈ $4.40` — one key hammering its full hourly allowance for an hour still can't burn through the existing `$20/month` cap on its own, and the existing monthly circuit breaker remains the true stop-loss across all keys combined.
- A request to a Tier 1 endpoint with no/invalid key → `401` with a body pointing at `POST /api/v1/keys`.

### 4. CORS

A small `after_request` hook (no new dependency — `flask-cors` is not needed for one static header) adds `Access-Control-Allow-Origin: *` **only** on Tier 0 (keyless, read-only, GET) routes — this is what actually lets a seminary/journal's client-side JS fetch cached results directly, the roadmap's stated goal.

Tier 1 (key-gated) and vote-write endpoints get **no** CORS headers — deliberately. A key used from arbitrary browser-side JS would be visible in page source; the intended integration path for the gated tier is server-to-server, so withholding CORS there is a safeguard, not an oversight.

---

## What this explicitly does NOT do (YAGNI cuts)

- No billing/payment integration — keys are free; BibCrit does not monetize the API.
- No per-key usage dashboard or self-service revoke/rotate UI — `requests_total`/`last_used_at` are captured now so a dashboard is a pure addition later, not a re-migration.
- No OAuth/JWT/user-accounts system — a static bearer-style key fits this scale.
- No Redis / shared rate-limit backend — justified above by the confirmed single-worker deployment; flagged as a must-revisit if that ever changes.
- Does not change the behavior of any existing bare `/api/...` route — aliased, not replaced.
- Does not add rate limiting or auth to `/health`.

---

## Testing

- Route aliasing: both `/api/cache` and `/api/v1/cache` return identical bodies for the same query.
- Key issuance: `POST /api/v1/keys` returns a key exactly once; the same key hashed and looked up succeeds; a `revoked` key is rejected with `401`.
- Rate limiting: Tier 0 IP throttle triggers a `429` past the per-minute/day threshold on a read endpoint; Tier 1 per-key throttle triggers a `429` past `20/hour` on a stream endpoint; a fresh key/IP is unaffected by another key/IP's usage (isolation).
- CORS: `Access-Control-Allow-Origin` header present on a Tier 0 GET response, absent on a Tier 1 stream response and on `POST /api/vote`.
- OpenAPI spec: `/api/v1/openapi.json` validates as OpenAPI 3.0 (e.g. via `openapi-spec-validator`); every path has both its versioned and (where applicable) deprecated-bare entry; `/api/docs` still renders Swagger UI without console errors against the updated spec.
- Existing behavior untouched: the full existing test suite (`tests/`) still passes unmodified — this work adds routes and gates, it doesn't alter any existing analysis logic.
