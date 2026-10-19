# Architecture Decisions (research-verified, October 2026)

Every major choice below was verified against external sources before implementation.
Sources were reached with: Exa websearch, openresearch (DuckDuckGo), free-search
(multi-engine), duckduckgo MCP, GitMCP (zhanymkanov/fastapi-best-practices),
paper-search (Semantic Scholar), wiki, Kaggle, GDELT news.

## 1. Frontend: Next.js 16 (App Router) + React 19 + TypeScript + Tailwind v4

Verified consensus (StarterPick, VibeReference, newstack.dev, Stackwise, 2026):
Next.js is the 2026 default for multi-tenant SaaS dashboards — largest ecosystem,
strongest auth/billing integrations, most mature multi-tenancy patterns
(middleware routing, server components, org-scoped data).

Rejected: SvelteKit (smaller ecosystem/hiring pool; strong at bundle size but we
ship a dashboard, not a content site), Nuxt (Vue-first; ecosystem gap for SaaS/AI
tooling), Astro (content-first; friction once the product is dashboard-shaped),
Remix/RR7 (identity muddled post-merge; no advantage for this product).

## 2. UI system: shadcn/ui-style copy-in components on Radix + Tailwind v4

Verified consensus (We.Inc, newstack.dev, Guideflow, StarterPick, PkgPulse, 2026):
shadcn/ui is the industry default for React SaaS (the style ships in ShipFast,
Supastarter, Makerkit, Open SaaS). We vendor the component source into
`src/components/ui` — full ownership, zero runtime CSS-in-JS, accessible Radix
primitives underneath.

Important documented risk (uxmagic.ai 2026): AI-generated SaaS UIs converge on
stock shadcn looks (slate palette, identical radii). Mitigation: custom design
tokens (deep-space dark theme, per-tenant accent color, distinctive typography
scale) instead of stock defaults.

## 3. Backend: FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic

Verified (Cadence 2026, wappnet 2026, Navspace 2026, EVNE 2026, meduzzen 2026):
- FastAPI for API-first products: 30–40k RPS vs 8–12k (DRF), async-first,
  Pydantic v2 validation, automatic OpenAPI for the frontend team.
- Django rejected: our app is API-first (separate Next.js frontend); Django's
  admin/templates add weight we do not use. (Django remains right for
  template-heavy full platforms.)
- SQLAlchemy 2.0 async + asyncpg (documented: sync drivers in async endpoints
  negate the concurrency benefit).
- Structure: domain-oriented modules (`router/schemas/models/service/dependencies`)
  per zhanymkanov/fastapi-best-practices (Netflix Dispatch pattern) fetched via GitMCP.
- Async httpx test client (ASGITransport) from day 0 — same source.
- Ruff for lint/format — same source.

## 4. Database: PostgreSQL 16, shared schema + tenant_id + Row-Level Security

Verified (OWASP Multi-Tenant Security Cheat Sheet; ClickHouse engineering 2026;
PlanetScale; drawDB 2026; AWS database blog):
- Shared tables + `tenant_id` on every tenant-owned row is the best default for
  new B2B SaaS in 2026 (Notion runs the pattern at 480 logical shards).
- Schema-per-tenant: rejected by two independent sources as operationally toxic
  (per-schema migrations, catalog bloat; "rarely the right pick in 2026").
- RLS as defense-in-depth with these mandatory rules (all verified):
  - `ENABLE` + `FORCE ROW LEVEL SECURITY` on every tenant table.
  - App connects as a role that owns nothing: `NOSUPERUSER NOBYPASSRLS`
    (superusers/owners silently bypass otherwise — the #1 RLS failure).
  - Tenant passed per transaction via `set_config('app.current_tenant', $1, true)`
    (transaction-local; safe with connection pooling / PgBouncer transaction mode).
  - Policy uses `NULLIF(current_setting('app.current_tenant', true), '')` so a
    missing tenant fails closed (zero rows), never errors or leaks.
  - Startup check: refuse to boot if the request role can bypass RLS or any
    tenant table is missing `relrowsecurity AND relforcerowsecurity`.
  - Indexes lead with `tenant_id`.
- Application code ALSO filters by tenant (both layers, per EF Core/Postgres guidance).
- `tenant` directory table stays global so a tenant can later be lifted to a
  dedicated database (hybrid pool→silo path) without application changes.

## 5. Proxy / TLS: Caddy 2 with automatic HTTPS; wildcard via DNS-01

Verified (Caddy docs pattern 2026, skeptrune wildcard TLS 2025, Traefik v3 guide
2026, compose examples): Caddy in front for wildcard subdomains
(`*.APP_DOMAIN`), on-demand/automatic certs; DNS-01 (Cloudflare token) when a
wildcard is needed. Traefik v3 acceptable alternative; Caddy chosen for the
smallest correct config.

## 6. Multi-tenancy product surface (the 10-pattern checklist, mapped)

| # | Pattern | Implementation |
|---|---------|----------------|
| 1 | Hybrid data isolation | RLS pool now; tenant directory + per-tenant DSN field reserved for silo moves |
| 2 | Compliance routing | per-tenant `region` field + config for data residency; EU/US deployment split documented |
| 3 | Self-serve provisioning | `POST /auth/register` creates tenant + owner + defaults atomically |
| 4 | Identity & RBAC | JWT (access+refresh) with `tid` claim; roles owner/admin/manager/agent/viewer |
| 5 | Billing & entitlements | plans table; boolean features + numeric quotas enforced server-side (Stripe-ready webhook module) |
| 6 | Noisy-neighbor throttling | per-tenant+IP rate limiting (Redis, in-memory fallback) |
| 7 | White-label + custom domains | tenant branding JSONB + `custom_domain` resolution endpoint used by frontend middleware |
| 8 | Encryption posture | secrets via env; TLS everywhere via Caddy; argon2id password hashing |
| 9 | Tiered feature flags | plan features merged with per-tenant overrides in one resolver |
| 10 | Per-tenant observability | audit_log per tenant; tenant slug in structured logs; per-tenant usage counters |

## 7. Billing/entitlements principle (verified: Stripe docs, cesarayala.dev 2026, maviklabs 2026)

Separate billing from entitlements: bills are provider events, entitlements are
enforced booleans + quotas checked per request in the backend. Provider-agnostic
module with a Stripe webhook sync endpoint (idempotent upsert), no hard
dependency on Stripe for self-hosted operation.

## 8. Booking concurrency (standard practice)

Seat inventory row (`train_inventory`, unique per tenant+train+date) is locked
with `SELECT ... FOR UPDATE` inside the booking transaction; overbooking
rejected with 409. Cancellation returns seats exactly once (status transition
guard). Multi-passenger bookings supported.

## 9. Data seeding

Kaggle has Indian Railways datasets (11k+ downloads) — deliberately NOT bundled:
licensing and relevance to global operators are poor, and operators import their
own data. Instead: realistic multi-region seed script + per-tenant CSV import
for trains and bookings export for reporting.
