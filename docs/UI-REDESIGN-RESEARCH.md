# UI Redesign Research — RailFlow (October 2026)

Purpose: every UI change in this redesign must be backed by a verified best practice.
No hand-edits without a cited rule. This document is the verification source.

Method: sequential searches (one at a time, never parallel) across Exa websearch,
free-search (multi-engine), openresearch, DuckDuckGo, agent-reach, Wikipedia,
paper-search (arXiv), Kaggle, semantic skill search, plus primary-source fetches
(W3C, OpenDesigner standards, emilkowalski/skills). Searches ran 2026-10-18.
gsd_websearch returned empty (Brave key not configured); gitmcp/searxng are not
available in this toolset and were substituted by `openresearch_read_repo` and
`free-search` multi-engine routing respectively.

---

## 1. Direction (locked)

**Emotion: calm + confident.** An operations console for railway operators: dense
but quiet, dark-first, numbers legible at a glance. Reinforce in every decision
instead of tacking delight on top (STD-visual-details-47).

Grammar: Linear (restraint, density, radius/spacing discipline) + Vercel (pure
black surfaces, no muddy grays) + Stripe (tabular numerics, generous body
leading). Sources: Exa search "best SaaS dashboard UI design 2026…".

**Dark-only for now.** Semantic tokens are structured for light/dark mapping
(STD-visual-details-24) but only the dark mapping ships in this pass.

---

## 2. Color system (OKLCH, dark)

Source: Exa search "dark mode UI design best practices OKLCH…" + Wikipedia
(Oklab, CSS Color 4) + STD-visual-details-21/24/25.

- Near-black base, NOT pure #000: ~`oklch(0.14 0.01 280)` page base.
- Elevation = lightness steps, not shadows: `+0.03–0.05 L` per layer.
  Surface ladder: base 0.14 → card 0.18 → overlay 0.24 → active/hover 0.32.
- Borders: semi-transparent hairlines `oklch(1 0 0 / 8–10%)`, never opaque solid
  (STD-visual-details-14: semi-transparent shadow/border over solid opaque).
- Text: off-white tiers ≈ L 0.93 / 0.72 / 0.52 (≈ 87% / 60% / 38% equivalent).
- Accent: brand purple `#6d5efc` → OKLCH (convert programmatically, verify in
  browser). Dark mapping: desaturate 15–25%, raise L ~5%.
- Max 2 accents per page (Linear rule). Accent used only for primary actions,
  active nav, focus, and data series — never decoration.
- 3-layer token architecture: primitive → semantic → component. Never hand-type
  a value (STD-visual-details-26); extend tokens for anything new.
- Contrast floors: 4.5:1 body text, 3:1 large text and non-text UI (WCAG 1.4.3,
  1.4.11, 2.4.7 as captured via openresearch WCAG 2.2 sweep); aim APCA Lc 75+
  for body text in dark mode.

## 3. Typography

Sources: Exa "product UI typography 2026…", OpenDesigner ui-details, STD-01…10.

- Inter Variable via next/font, self-hosted at build; metric-matched fallback
  stack to avoid layout shift (STD-visual-details-10).
- Role-based scale (UI base 13–15px desktop; use 14px):
  - page title 24/1.25 weight 600, tracking -0.02em
  - section 16/1.4 600
  - body 14/1.5 400
  - small/meta 12.5/1.45 400
  - table cell 13
- Letter-spacing by size: tighten large (-0.02em), near 0 body, slightly
  positive small; uppercase labels get looser tracking (STD-04, STD-05).
- Line-height inversely with size: 1.05–1.25 headings, 1.5 body (STD-06).
- Hierarchy from weight + size + leading together (STD-07). Emphasise with
  weight, never italic (STD-08). Underline only links (STD-09).
- `font-variant-numeric: tabular-nums` on every price, count, date and metric
  (STD-visual-details-02). Numbers that animate use NumberFlow (STD-59).
- Ellipsis character "…", never three periods (STD-03).
- Body text capped at 65ch (STD-01).
- Inputs ≥16px font (prevents iOS zoom; STD-mobile-touch-11 / WCAG floor).

## 4. Spacing, layout, radii

Sources: Linear rules (Exa dashboard search), STD-27/28/29/31/32/33/34.

- 4px grid; common steps 4/8/12/16/24/32; section spacing 32–48 in-app,
  64–96 on marketing.
- Sidebar 240–280px (use 248px). Content max-width ~1200px for tables,
  65ch for prose.
- Radius: ≤8px everywhere (Linear rule); concentric radii — outer = inner +
  padding (Tailwind v4 @theme guidance). Cards 10px is allowed only if it
  reads as a deliberate surface; default 8.
- Every value deliberate; no jitter, no misaligned icons, no rotation breaks
  (STD-27/28).
- Hierarchy: the most important thing is the most obvious (STD-29).
  Common path first, advanced one level deeper (STD-31).
- Controls sit near what they change (STD-32). Wayfinding: every screen answers
  where am I / where can I go / what's there / how do I get out (STD-33).
- Nav named for contents (Trains, Bookings, Reports, Team, Audit, Settings) —
  never vague umbrellas (STD-34).

## 5. Materials and elevation

Sources: OpenDesigner ui-details, STD-14…21, Apple-derived rules.

- Separate surfaces with semi-transparent borders/shadows, not opaque lines.
- Sticky header: scroll-edge fade (blur/gradient mask) where content passes
  under it — NO permanent 1px divider (STD-15). 
- Translucent chrome where it floats: `backdrop-filter: blur(20px)
  saturate(180%)` over `oklch(1 0 0 / 6%)` (STD-16).
- Never stack two light translucent surfaces (STD-18). Bigger surfaces read
  thicker: stronger blur + deeper shadow than chips (STD-19).
- Modals get a dimming scrim; side panels don't (STD-20). Color lives on solid
  layers, not translucent ones (STD-21).

## 6. Motion (locked tokens)

Sources: OpenDesigner standards v3 locked values + emilkowalski/skills
(emil-design-eng) + Exa motion search. All values become CSS variables in
`@theme` — never hand-typed cubic-beziers (STD-visual-details-26).

Token table (adopt verbatim):

| Token | Value |
|---|---|
| duration.instant | 0ms |
| duration.micro | 100ms |
| duration.short | 150ms |
| duration.medium | 200ms |
| duration.long | 250ms |
| easing.enter / easing.exit | cubic-bezier(0.23, 1, 0.32, 1) |
| easing.standard (moving) | cubic-bezier(0.77, 0, 0.175, 1) |
| easing.hover | cubic-bezier(0.25, 0.1, 0.25, 1) |
| easing.linear | linear |
| easing.drawer | cubic-bezier(0.32, 0.72, 0, 1) |
| scale.enter (popover/dialog) | 0.95 / 0.96 |
| scale.enter-tooltip | 0.97 |
| scale.press | 0.97 |
| duration.tooltip | 125ms |
| duration.modal | 250ms |
| stagger | 50ms (range 30–80ms) |
| toast enter | 400ms, ease hover-curve; auto-dismiss 4000ms; max 3 visible; gap 14px; offset 32px desktop / 16px mobile |
| reduced motion | replace movement with 200ms opacity fade |

Framework rules (emil-design-eng, verified against the skill file):

1. Frequency gate: 100+/day → no animation ever (keyboard-initiated:
   command palette, shortcuts). Tens/day → drastically reduce. Occasional
   (dialogs, drawers, toasts) → standard. Rare/first-time (onboarding,
   landing) → can add delight.
2. Easing: entering/exiting → ease-out; moving/morphing → ease-in-out;
   hover/color → ease; constant → linear. NEVER ease-in (starts slow, feels
   sluggish).
3. Never animate from scale(0); start at 0.95–0.97 + opacity.
4. Popovers scale from their trigger (`transform-origin` from trigger);
   modals stay centered.
5. Exit faster than enter (~20% faster).
6. Only transform/opacity (GPU). Use CSS transitions over keyframes for
   interruptible UI; @starting-style for entry; translateY(±%) for
   toasts/drawers; blur(2px) to mask imperfect crossfades; `<20px` blur.
7. Press feedback: scale(0.97) on :active, 100–160ms.
8. Hover effects only under `@media (hover:hover) and (pointer:fine)`.
9. `prefers-reduced-motion`: keep opacity/color, remove movement.
10. Stagger 30–80ms; decorative only; never block interaction.
11. Tooltips: 125ms, scale 0.97, instant on subsequent hovers.
12. No entrance animations on dashboard surfaces (metric cards, charts,
    tables) — micro-interactions only.

## 7. Feedback, state, and copy

Sources: STD-40, STD-49, STD-35, STD-50/51, break-ui patterns.

- Every action gets feedback: loading state while submitting, success state
  after (toast), ongoing status, warnings before problems, inline validation
  (on blur) instead of on submit (STD-49).
- Undo for slips; confirmation dialogs only for genuinely destructive,
  irreversible actions, sparingly (STD-40). Cancel Booking keeps a
  confirmation (seat impact); avoid confirms elsewhere.
- Empty states teach: one line + one action + illustration-free icon
  (dashboard principle "empty states that teach" + first-90-seconds).
- Skeletons, not spinners, for content; pulse 1.5s; static under reduced
  motion; skeleton geometry matches final layout (no shift).
- Plain, concise copy; sentence case; no jargon (STD-35).
- Same look, same behaviour, same place (STD-36). Don't break familiar
  patterns without proof (STD-37).

## 8. Components

Sources: OpenDesigner curated library list (STD-55/56/57/59), emil-design-eng,
cmd+K research (duckduckgo sweep), Base UI vs Radix research (Exa).

Library decisions:

- **Keep** Recharts (curated list: "other charts: recharts"; 2026 reviews
  confirm it as the default for React dashboards, SSR-safe, shadcn-compatible).
- **Keep** Radix primitives (STD-56: don't churn a working dependency;
  base-ui is the curated pick for new projects and shadcn's July-2026 default —
  recorded as the future migration path, not a now-task).
- **Keep** TanStack Query for server state; add **zustand** only if client
  shared state outgrows context (STD-61).
- **Add** sonner (toasts; STD-57 — never hand-roll), cmdk (command palette),
  motion (dialog/drawer/list animation; motion/react),
  @number-flow/react (animated numbers; STD-59).

Component specs:

- **Buttons**: press scale(0.97) 100ms; focus ring 2px/2px-offset ≥3:1;
  loading spinner fast; disabled = muted surface + no press.
  Primary = accent on solid layer; secondary = surface step 0.24 hairline;
  ghost = hover surface only.
- **Inputs**: 16px text, 40px height, hairline border, focus = 2px ring +
  border accent; error = danger text under field; label sentence case.
- **Dialog**: centered (origin center), scale 0.96 + fade in 250ms
  ease-enter; exit 200ms (faster); scrim dim; focus trapped; ESC closes.
- **Popover/dropdown/menu**: origin-aware, scale 0.95 + fade 200ms;
  exit 150ms.
- **Tooltip**: 125ms, scale 0.97, instant subsequent.
- **Drawer (mobile nav)**: ease-drawer curve; enter 300ms, exit 200ms
  (frequency: tens/day → reduced); overlay tap + ESC close; focus trapped.
- **Toasts**: Sonner. gap 14, max 3, 4s, bottom-right desktop 32px /
  bottom 16px mobile; success/error/info with action button ("Undo" where
  cheap); pause on hover default.
- **Command palette (⌘K / Ctrl-K)**: cmdk; NO open/close animation
  (keyboard-initiated, 100+/day); ARIA combobox with aria-activedescendant;
  fuzzy match with consecutive + word-boundary scoring; actions: navigate,
  create booking, create train, toggle theme later; frecency later; 8 states
  covered (empty query, no results, loading, error).
- **Tables**: sticky header with scroll-edge fade (no hard divider); density
  40px rows; left-align text, right-align numerics with tabular-nums; header
  alignment matches cells; never center; sort indicators with aria-sort;
  "Showing X–Y of Z"; filters visible above (no hidden drawers);
  status = dot + label chip; dates left-aligned; units in header, not cells.
- **Skeletons**: per-surface geometry true to content; pulse animation.
- **Empty state**: icon, one-line explanation, primary action, optional hint.

## 9. Charts and data

Sources: arXiv sweep (drill-down/progressive disclosure; misleading-axis
literacy), Exa dashboard + Stripe rules.

- Recharts; flat fills (accent at low alpha), no gradients (Linear rule).
- Honest axes: bar/area baselines at zero; no truncated scales.
- Grid = hairline border color; axis labels 11–12px text-tertiary; no legend
  when a single series is self-evident via title.
- Tooltip: instant after first; tabular numerals; currency formatted via
  existing `money()` helper.
- 4–6 KPIs above the fold max; delta chips (↑/↓, semantic color, small text);
  NumberFlow for the animated value (mount only; none under reduced motion).
- Drill-down over density: summary first, detail one level deeper (STD-31).

## 10. Landing page (selling)

Sources: free-search landing sweep, pricing sweep, motion frequency rules.

- Hero: value proposition readable in 3 seconds; ONE primary CTA above the
  fold ("Start free trial"-style, states what happens next); secondary CTA
  later.
- No over-design: heavy animation and assets measurably cost conversions.
- Sections: hero → product screenshot/console → 3–4 feature blocks → pricing
  preview (3 tiers, middle dominant) → social-proof slot → FAQ → final CTA.
- Pricing section spec: 3 tiers; middle = visually dominant (accent border,
  elevation, honest "Most popular" badge only if true); annual/monthly toggle
  showing monthly equivalent ("$49/mo billed annually"), explicit savings;
  4–6 features per card with "Everything in X, plus…"; tier-specific CTA
  labels; reassurance line near CTAs ("Cancel anytime"); FAQ answers top
  objections; no fake urgency.
- Motion on marketing pages is allowed to be delightful (rare/first-time) but
  stays sub-300ms for UI micro and ≤600ms for reveals, staggered 30–80ms,
  reduced-motion aware.

## 11. Accessibility floors (must pass)

Sources: WCAG 2.2 sweep (W3C, Level Access, getwcag), OpenDesigner floors.

- 24×24 CSS px minimum target (WCAG 2.5.8 AA); we ship 44px touch targets and
  24px minimum everywhere.
- Focus visible: 2px ring, 2px offset, ≥3:1 contrast (WCAG 2.4.7, 1.4.11).
- Focus never obscured by sticky chrome (WCAG 2.4.11).
- Text contrast 4.5:1 (3:1 large); never round up (4.49 fails).
- Inputs ≥16px; never disable pinch zoom.
- Keyboard path for every action; visible focus at all times; ESC closes
  overlays.
- `prefers-reduced-motion` global block; hover gated by input media queries.

## 12. Implementation plan (files)

1. `frontend/src/app/globals.css` — full token layer v2: OKLCH primitives →
   semantic vars → motion tokens → focus ring global → reduced-motion block →
   scroll-edge utility → skeleton keyframes.
2. `frontend/src/app/layout.tsx` — Inter Variable via next/font with
   metric-matched fallback; mount `<Toaster />`; theme-color meta.
3. `frontend/package.json` — add sonner, cmdk, motion, @number-flow/react.
4. `frontend/src/components/ui/*` — restyle per §8 (button, input, dialog,
   dropdown, popover, tooltip, badge, card, skeleton, table, tabs, toast,
   command palette new).
5. `frontend/src/components/app-shell.tsx` — 248px sidebar, active states,
   scroll-edge header, mobile drawer per §8, command palette trigger.
6. Pages: dashboard (KPI row + charts + recent list, empty states), trains,
   bookings (dense table + filters), reports, team, audit, settings, billing
   (pricing cards per §10), login/register (craft pass), landing (full
   marketing rebuild), not-found.
7. Verify: tsc + eslint + build; Playwright screenshots (1440×900, 390×844);
   console clean; worst-case data pass (long names, huge counts, empty lists —
   "break-ui" checklist); keyboard-only pass; reduced-motion emulation.
8. Rebuild frontend image, redeploy compose stack, smoke at :8095.

## 13. Sources

- Exa websearch (7 sequential queries): dashboard 2026 principles; dark-mode
  OKLCH tokens; typography (Inter/Geist, tabular nums); motion durations and
  easings; Tailwind v4 @theme; Base UI vs Radix (shadcn July-2026 default);
  data-table UX; chart-library 2026 comparison.
- OpenDesigner: ui-details page; standards.md (455-rule index + locked motion
  values); standards/visual-details.md (55 rules STD-01…64) —
  https://opendesigner.vercel.app/docs/ui-details/ ,
  https://github.com/ckryptickunal/OpenDesigner (skills/opendesigner/references).
- emilkowalski/skills (47k★; ex-Vercel/Linear): emil-design-eng skill file —
  animation decision framework, review checklist, Sonner principles —
  https://github.com/emilkowalski/skills . Essay: Agents with Taste —
  https://emilkowal.ski/ui/agents-with-taste
- free-search multi-engine: SaaS landing page best practices 2026;
  React chart libraries 2026 (LogRocket, wpdatatables, PkgPulse).
- openresearch: WCAG 2.2 (W3C TR, Level Access 2026-02-23, getwcag
  2026-08-25, web-accessibility-checker 2026-08-16).
- duckduckgo: command palette patterns (uxpatterns.dev, mobbin, jsbits,
  setproduct 8-states teardown).
- agent-reach: pricing page UX (Figma resource library; BuiltUX 2026-10-16;
  digitalapplied 2026-05-27; Baymard 37% badge lift; redhub on honest
  signals vs cargo cult).
- Wikipedia: Oklab color space (Björn Ottosson 2020; CSS Color 4).
- paper-search (arXiv): drillboards (adaptive drill-down dashboards,
  2410.12744); visualization misinformation taxonomy (MisVisFix 2508.04679 —
  axis honesty).
- Kaggle: UI-Elements-Detection / WebTemplates datasets reviewed — not needed
  for this pass (recorded for completeness).
