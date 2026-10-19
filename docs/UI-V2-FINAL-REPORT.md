# RailFlow UI v2 — Final Report

Date: 2026-10-19 · Scope: full frontend redesign ("from zero to hero") + verification
Governing document: `docs/UI-REDESIGN-RESEARCH.md` (every change traces to a rule below)

---

## 1. Outcome

The console was rebuilt on a new design system rather than restyled ad hoc. All 14 app screens,
auth flows, landing page, and the shell now share one visual grammar: calm dark surfaces, a single
violet accent, hairline borders, 4px spacing grid, tabular numerals, and motion that is fast and
directional.

**Status: complete, deployed, verified.** `frontend`, `backend`, `db`, `redis`, `caddy` all running;
`http://localhost:8095` serves the new build.

---

## 2. Design system (locked decisions → implementation)

| Area | Rule (research §) | Implementation |
|---|---|---|
| Direction | "calm + confident", Linear/Vercel/Stripe grammar (§2) | Flat surfaces, no gloss, one accent per view |
| Color | OKLCH base `0.14 0.01 280`, surface ladder 0.14/0.18/0.24/0.32 (§3) | `globals.css` semantic tokens; no raw hex in components |
| Accent | `#6d5efc`, max 2 accents per page (§3.4) | Primary actions + one data series only |
| Contrast | 4.5:1 text, APCA Lc 75+ (§3.6) | Text tiers L 0.93 / 0.72 / 0.52 on 0.14–0.18 surfaces |
| Type | Inter Variable, page title 24/1.25 w600 -0.02em (§4) | Self-hosted `next/font`, `tabular-nums` on all numerics |
| Spacing | 4px grid, sidebar 248px, content `max-w-6xl` (§5) | Applied in shell + every page container |
| Radii | ≤ 8px; `rounded-full` only for pills/dots/switches (§5.3) | Audited: zero decorative `rounded-full` |
| Materials | No decorative gradients; no stacked translucency (STD-18) (§6) | Only gradient left is the scroll-edge fade utility |
| Sticky header | Scroll-edge fade, not a divider (§6.4) | `.scroll-edge` in `@layer components` |
| Floating chrome | `blur(20px) saturate(180%)` over 6% white (§6.5) | Command palette, toasts |
| Motion | 100/150/200/250ms tokens, enter `cubic-bezier(0.23,1,0.32,1)` (§7) | Tokens in `globals.css`; no `ease-in` anywhere |
| Charts | Flat fills, baseline 0, hairline grid, no gradients (§9) | Recharts: area `#6d5efc` @ 0.12 flat, bars `#22d3ee` @ 0.35 |
| Landing/pricing | One primary CTA, 3 tiers, middle dominant, annual toggle (§10) | Rebuilt hero, mock console, tier CTAs, FAQ |
| A11y | 24×24 targets, 2px focus ring offset 2px, ESC closes (§11) | Verified in browser (below) |

---

## 3. What was rebuilt

- **Foundations** — `globals.css` v2 (tokens, motion, scroll-edge), `layout.tsx` (Inter), toaster.
- **UI kit (14 components)** — button, input, label, card, badge, table, dialog, select, switch,
  tabs, tooltip, skeleton, empty-state, pagination — all re-skinned to tokens.
- **New** — `command-palette.tsx` (cmdk, ⌘K), `lib/use-deep-link.ts`.
- **Shell** — `app-shell.tsx` rebuilt: 248px sidebar, sticky top bar with scroll-edge fade,
  mobile drawer + bottom-of-header nav, plan card.
- **Pages** — dashboard, bookings, trains, reports, team, audit, settings, billing.
- **Auth** — login (split panel + demo card), register, not-found.
- **Landing** — full rewrite: hero with one CTA, mock console, feature grid, 3-tier pricing with
  annual toggle, FAQ, footer.

---

## 4. Verification performed (live, on `:8095`)

**Build gates**
- `npx tsc --noEmit` — clean
- `npx eslint src --max-warnings=0` — clean
- `npm run build` — 14 routes compiled
- Docker image rebuilt and redeployed; `/` returns 200

**Desktop sweep (1440×900)** — all 8 app pages, console clean on each:
- Dashboard: 4 KPIs, latest bookings, at-a-glance panel
- Bookings: 16 rows, sticky `th` confirmed (`position: sticky`, stays at 232px through 75px scroll),
  footer "Showing 1–16 of 16", single-line train/date/contact cells
- Trains: 8 rows, day pills, switches, "1–8 of 8"
- Reports: KPI row, chart compliance verified in DOM — `gradients: 0`, flat area fill, 8 bars,
  hairline grid, tooltip hidden when inactive; cancellation hint now "2 cancelled"
- Team: "4 of 15 seats used", role selects, self-switch disabled
- Audit: 10 rows, filters, collapsible payloads, placeholder "Action contains…"
- Billing: plan cards, correct check/minus states, quota bars
- Settings: branding editor with labelled swatches (`aria-label` + `aria-pressed`), preview

**Mobile (390×844)**
- Bookings: `pageOverflow: 0`, table scrolls horizontally, sidebar hidden, mobile nav present,
  no sub-24px targets, all cells single-line
- Login: no horizontal overflow, demo card visible below the form

**Interaction & a11y**
- Focus ring on nav link: `outline: 2px solid rgb(109,94,252)`, `offset: 2px` — matches §11
- ⌘K opens the command palette; `Escape` closes it
- `prefers-reduced-motion` rules present (global + Sonner)
- Login: demo credentials fill and submit successfully ("Welcome back, Dana")

**Screenshots** — 18 `v2-*.png` in `/home/md/src/.playwright-mcp/`.

---

## 5. Fixes applied in the final pass

1. Reports — cancellation hint derived from rate (`Math.round(rate × bookings_30d)`) instead of
   showing the train count.
2. Audit — search placeholder shortened so it no longer truncates.
3. Settings — palette swatches given `aria-label` + `aria-pressed`; password field
   `autoComplete="new-password"`.
4. Bookings — `whitespace-nowrap` on train, travel-date and contact cells (mobile wrapping).

---

## 6. Known assumptions & backlog

**Assumption to confirm:** annual pricing uses `ANNUAL_MONTHS = 10` (i.e. "2 months free"), and the
monthly-equivalent display is `price_cents × 10 / 12`. This is a UI-only convention — checkout is
via `mailto:sales@` — so it must be confirmed before wiring a real payment provider.

**Not done (offered, awaiting direction):**
- `git init` + initial commit (the tree is not under version control)
- Real Stripe billing (currently plan changes are recorded, not charged)
- White-label theme editor beyond the existing preset palettes
