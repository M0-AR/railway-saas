# RailFlow frontend

Next.js 16 operator console for the RailFlow multi-tenant railway SaaS.
Dark-first, server-proxied API, per-tenant white-label branding.

## Stack

Next.js 16 (App Router, Turbopack, Cache Components) · React 19 · TypeScript (strict) ·
Tailwind CSS v4 · Radix primitives (source-owned, shadcn-style) · TanStack Query ·
Recharts · lucide-react.

## Development

```sh
npm install
npm run dev          # http://localhost:3000
```

The dev server needs the API. Either run the backend directly
(`cd ../backend && ./.venv/bin/uvicorn app.main:app --reload`, reachable at
`http://127.0.0.1:8000`) or start the whole stack with compose and use
`http://localhost:8080` (see the root `README.md`).

Without a proxy, requests go to `NEXT_PUBLIC_API_BASE` (default `/api/v1`), which
only resolves when something fronts both apps (Caddy in compose). For local UI work
against a bare backend, set `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api/v1`.

Seeded demo login: workspace `demo`, `demo@railway.demo` / `demo1234`.

## Scripts

| Script              | What it does                                  |
| ------------------- | --------------------------------------------- |
| `npm run dev`       | Dev server with Turbopack                     |
| `npm run build`     | Production build (standalone output)          |
| `npm run start`     | Serve the production build                    |
| `npm run typecheck` | `tsc --noEmit`                                |
| `npm run lint`      | ESLint                                        |
| `npm run test`      | Vitest unit/component suite (60 tests)        |
| `npm run test:coverage` | Vitest with coverage thresholds           |
| `npm run e2e`       | Playwright E2E + a11y (stack on :8095)        |

Testing details and evidence: [`../docs/TESTING.md`](../docs/TESTING.md).
E2E needs the compose stack: `make fe-e2e-up` from the repo root. Visual
snapshots are opt-in via `E2E_VISUAL=1 npm run e2e`.

## Environment

| Variable               | Default     | Notes                                                |
| ---------------------- | ----------- | ---------------------------------------------------- |
| `NEXT_PUBLIC_API_BASE` | `/api/v1`   | Browser API base; inlined at build time               |
| `API_INTERNAL_URL`     | `http://127.0.0.1:8000` | Runtime-only, used by `serverApi()`     |
| `NEXT_PUBLIC_APP_DOMAIN` / `APP_DOMAIN` | `localhost` | Domain used to derive `<slug>.<domain>` tenants |
| `PORT` / `HOSTNAME`    | `3000` / `0.0.0.0` | Consumed by `node server.js` (standalone)     |

## Multi-tenancy

`src/proxy.ts` (Next 16's `middleware` successor) derives the workspace slug from
`?tenant=<slug>` or `<slug>.<APP_DOMAIN>` and stores it in the `rf_slug` cookie;
login/register pages prefill from it. Auth uses bearer tokens (localStorage,
`rf_access_token` / `rf_refresh_token` / `rf_me`) with a single-flight refresh on
401. Branding from the tenant record is applied as CSS variables on the app shell,
login/register pages and the landing page.

Navigation is role-aware (team/audit/settings/billing are owner/admin) and
feature-aware (CSV import, advanced analytics and audit log surface upgrade cards
when the plan does not include them).

## Routes

`/` landing · `/login` · `/register` · `/dashboard` · `/trains` · `/bookings` ·
`/reports` · `/team` · `/audit` · `/settings` · `/billing`

## Docker

```sh
docker build -t railflow-frontend .
docker run --rm -p 3000:3000 -e API_INTERNAL_URL=http://host.docker.internal:8000 railflow-frontend
```

Multi-stage build on `node:22-alpine`, Next `output: "standalone"`, runs as the
non-root `nextjs` user, includes a container healthcheck on `/login`.
