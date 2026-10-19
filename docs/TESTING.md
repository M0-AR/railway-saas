# Testing & verification

This document is the map of the RailFlow verification system: what each tier
covers, how to run it, the gates that must stay green, and the evidence
produced by the last full run.

Design principle: **risk-based verification**. Every externally observable
behaviour (auth, tenancy, money, inventory, quotas, branding) has a test at the
lowest tier that can prove it, and the layers above prove the seams between
systems — not a claim of "100% bug-free", but a chain of evidence.

```
            ┌─────────────────────────────────────────────┐
  Tier 4    │ Playwright E2E · chromium + mobile · a11y   │  30 checks
            │ (real stack, Caddy → Next → FastAPI → PG)   │
            ├─────────────────────────────────────────────┤
  Tier 3    │ k6 load/concurrency (opt-in, infra/k6)      │  SLO thresholds
            ├─────────────────────────────────────────────┤
  Tier 2    │ Vitest component/unit (60 tests, 7 files)   │  90/90/85/90 coverage
            ├─────────────────────────────────────────────┤
  Tier 1    │ pytest (107 tests, 22 modules) + Hypothesis │  75% gate (currently 81%)
            └─────────────────────────────────────────────┘
```

## Tier 1 — Backend (pytest)

```sh
docker run -d --name railway-pg -p 5432:5432 \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=railway \
  -v "$PWD/infra/postgres/init:/docker-entrypoint-initdb.d:ro" postgres:17-alpine

cd backend
TEST_PG_PORT=5432 ./.venv/bin/python -m pytest -q          # full suite
TEST_PG_PORT=5432 ./.venv/bin/python -m pytest --cov=app   # with coverage
./.venv/bin/ruff check app tests
```

Harness notes:

- `conftest.py` recreates a dedicated `railway_test` database per session with
  `railway_owner`, runs Alembic, and **truncates every table between tests**
  (`TRUNCATE tenant CASCADE`), so each test owns its data.
- The seeded workspace fixture runs the real `seed_all()` per test, exercising
  the same code path as production boot.
- Property-based tests (Hypothesis) cover money/seat arithmetic and PNR/format
  invariants; RLS tests prove policies are enabled, forced and cannot be
  bypassed by the runtime role.

What is covered per area (107 tests in 22 modules):

| Area | Highlights |
|---|---|
| Auth | register/login/refresh, inactive member and suspended tenant rejection, refresh-token type confusion, generic login errors |
| Tenancy / RLS | cross-tenant reads and writes fail closed, `set_tenant_context` transaction-local, owner cannot bypass `FORCE RLS` |
| Bookings | overbooking 409 with `seats_left`, unique PNR retry, cancel/refund lifecycle, passenger totals, filters/pagination |
| Entitlements / billing | plan catalog, quota 402s, feature gating, per-tenant overrides, Stripe webhook plan flip |
| Trains | CRUD, CSV import (quota-aware), export, activation toggles |
| Team / RBAC | role matrix enforcement, invite temporary passwords, role changes |
| Rate limits | sliding window unit tests, per-IP and per-tenant middleware keys, health exemptions, 429 envelope |
| Seed | idempotency, realistic ledger, PII safety, tenant isolation, end-to-end usability via the API |
| Audit / reports / settings | action log filters, revenue/occupancy math, branding persistence |
| Health / contract / schema | probe endpoints, OpenAPI error-envelope contract, migration integrity |

## Tier 2 — Frontend (Vitest + Testing Library)

```sh
cd frontend
npm run test              # 60 tests, 7 files
npm run test:coverage     # enforces statements 90 / functions 90 / branches 85 / lines 90
```

Coverage scope is `src/lib/**` (API client, session, formatting, plans,
branding, deep links) plus the login form component. Current result:
**100% statements/lines/functions, 92.4% branches**. `slugify` was corrected to
match backend slug semantics as a direct result of this suite.

## Tier 3 — E2E, accessibility, visual (Playwright)

Requires the stack on port 8095:

```sh
make fe-e2e-up            # HTTP_PORT=8095 HTTPS_PORT=8495 docker compose up -d --build
cd frontend
npm run e2e               # 30 checks: chromium + mobile-chrome
E2E_VISUAL=1 npm run e2e  # adds 4 screenshot comparisons
```

The compose defaults set permissive rate limits for this profile
(`AUTH_RATE_LIMIT_PER_MINUTE=1000`) so parallel tests are not throttled;
production sets its own budgets.

What runs:

- **auth.spec** — anonymous redirect with `next` hop, tenant branding on the
  login page, single error for bad credentials, seeded demo login.
- **workspace.spec** — seeded fleet (12 trains), ledger (`1–20 of 48`),
  growth analytics, audit entries, demo team, settings branding, and the
  starter-plan upgrade gate.
- **a11y.spec** — `@axe-core/playwright` WCAG 2.1 A/AA scan of login,
  dashboard, trains, bookings and reports; fails on any serious/critical
  violation (zero today).
- **visual.spec** — opt-in screenshot regression for login and the trains
  workspace; baselines live in `e2e/visual.spec.ts-snapshots/` and are
  refreshed with `E2E_VISUAL=1 npx playwright test visual --update-snapshots`.

Accessibility findings were fixed in the app, not silenced: tertiary text
token `--ink-2` was lightened to meet 4.5:1, icon-labelled selects received
`aria-label`s, scrollable table containers are keyboard-focusable, and the
revenue chart exposes a labelled `role="img"` instead of an `aria-hidden`
focusable subtree.

## Tier 4 — Load (k6)

```sh
k6 run infra/k6/load-test.js                       # load profile (default)
SCENARIO=smoke  k6 run infra/k6/load-test.js       # 1 VU / 30s
SCENARIO=stress k6 run infra/k6/load-test.js       # up to 50 VUs
BASE_URL=http://demo.localhost:8095 k6 run infra/k6/load-test.js
```

The script logs in once (`setup`), then per VU reads overview/trains/bookings
and creates a booking (409 when seats run out is accepted as a correct
outcome). Thresholds: `http_req_failed < 1%`, `p(95) < 500 ms`.

k6 is not part of the default CI run; install it locally
(<https://grafana.com/docs/k6/latest/set-up/install-k6/>) or add the
`grafana/setup-k6-action` job when a target environment exists.

## Continuous integration

`.github/workflows/ci.yml` runs three jobs:

1. **backend** — Postgres service (init script creates `railway_owner` /
   `railway_app`), `ruff`, `pytest` with `--cov-fail-under=75`.
2. **frontend** — `npm ci`, lint, typecheck, Vitest coverage thresholds,
   production build.
3. **e2e** — builds and boots the full compose stack on ports 8095/8495,
   waits for `/healthz`, runs Playwright (chromium + mobile, including a11y
   and visual snapshots), uploads the HTML report and stack logs on failure.

## Optional: mutation testing

Budget permitting, `mutmut` on `backend/app/bookings` and
`backend/app/identity` gives a stronger signal than line coverage:

```sh
cd backend
pip install mutmut
mutmut run --paths-to-mutate app/bookings,app/identity
mutmut results
```

## Last full-run evidence (2026-10-19)

| Tier | Command | Result |
|---|---|---|
| Backend lint | `ruff check app tests` | clean |
| Backend tests | `pytest -q` | **107 passed** (~14s) |
| Backend coverage | `pytest --cov=app` | **81%** (seed 93%) |
| Frontend unit | `vitest run` | **60 passed** (7 files) |
| Frontend coverage | `vitest run --coverage` | 100% stmts/lines/funcs, 92.4% branches |
| E2E | `playwright test` | **30 passed** (chromium 15, mobile 15) incl. a11y + visual |
| Frontend static | `tsc --noEmit`, `eslint` | clean |

## Known gaps (deliberately out of scope)

Real Stripe checkout, DB backup/restore drills, refresh-token rotation,
observability/alerting, email delivery tests, SSO/SCIM, GDPR/DSAR tooling, and
full k6 runs in CI. Each is tracked as product work, not silently skipped.
