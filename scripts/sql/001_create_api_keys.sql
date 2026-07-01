-- scripts/sql/001_create_api_keys.sql
-- BibCrit Open API v1 — API key storage.
-- Raw keys are never stored; only their SHA-256 hash. RLS is enabled with
-- ZERO policies (default-deny) — only the Flask backend, via the Supabase
-- service-role key already in .env as SUPABASE_KEY, ever touches this table.
-- See docs/superpowers/specs/2026-07-01-open-api-v1-design.md for the design.

create table public.api_keys (
    id              uuid primary key default gen_random_uuid(),
    key_hash        text not null unique,
    key_prefix      text not null,
    owner_name      text not null,
    owner_email     text not null,
    created_at      timestamptz not null default now(),
    last_used_at    timestamptz,
    revoked         boolean not null default false,
    requests_total  bigint not null default 0
);

alter table public.api_keys enable row level security;
