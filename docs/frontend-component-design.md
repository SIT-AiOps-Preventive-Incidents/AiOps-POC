# 1. UX/UI Design & 3. Frontend: Component Design

Vue 3 (Composition API, `<script setup>`) + Vite + Pinia + Vue Router. Source: [`frontend/src`](../frontend/src).
60 `.vue` files, about 2,800 lines. A living style guide is part of the app: **Design System** page (`/#/design`).

## 1. UX/UI concept

| Decision | Why it fits the users (DevOps/SRE, service owners) |
|---|---|
| **Azure white & blue + Apple system font, iOS layout** (large titles, inset grouped lists, switches, segmented controls, sheets) | Familiar, calm, readable at 3 a.m.; Azure blue matches the Microsoft Teams world the alerts go to. |
| **One question per screen**: Home = "is anything wrong?", Problem = "what happened and what should I approve?" | The old UI showed everything at once; owners could not find the approve button. |
| **Problem page reads top to bottom like a story**: progress stepper → what happened → evidence → runbook → how the AI investigated (collapsed) | Owners need the conclusion first and the proof second; the agent's raw steps are available but out of the way. |
| **The decision is a single large button** with the dry-run checklist directly above it and an "I'm the owner" switch | Nothing can run without reading what will change and confirming ownership. |
| **Connecting is one command** (computer) or a 3-step wizard (app) with live "waiting → connected" feedback | Users said connecting was the hardest part. The screen tells them when it worked. |
| **Service map left-to-right by call depth, host lanes for discovered services, a "Send test request" that animates every hop** | Makes the request path tangible and shows where time is spent without reading a trace. |
| **Semantic colour only for state** (green ok, red problem, purple AI, orange warning); brand blue only for actions | Status is visible at a glance and never confused with buttons. |
| Real logos (Fluent UI icons, Devicon, Simple Icons) instead of drawn icons | Recognisable technologies; consistent icon grid. |
| **Light and dark mode** (Auto follows the OS; toggle in the top bar and in Settings). Every colour is a token in `tokens.css` with a dark value; nothing in a component is hard-coded | Operators work at night and in dark NOCs; the choice is remembered per browser and applied before first paint (no white flash). |
| Responsive: sidebar becomes a drawer < 760 px, sheets become bottom sheets, grids collapse | On-call engineers approve from their phone. |
| Accessibility: focus ring on every control, `role=switch/radiogroup/meter`, `aria-live` toasts, reduced-motion respected (map animation is skipped) | |

## 3. Component architecture

```
src/
├─ styles/tokens.css        design tokens (colour, type, spacing, radius, shadow, motion)
├─ styles/base.css          element styles + layout primitives (.page .grid .split .stack)
├─ lib/                     JS library - plain functions, no Vue
│   ├─ api.js               REST client for /api/v1, ApiError (status, code, details)
│   ├─ format.js            pct, ms, ago, dur, clock, slug
│   └─ vocab.js             status → label/tone, kind → icon, language/OS → logo
├─ composables/             reusable Vue logic
│   ├─ usePolling.js        refresh while mounted and the tab is visible
│   └─ useClipboard.js      copy with a fallback for plain-http hosts
├─ stores/ (Pinia)          global state shared by many components
├─ components/ui/           25 design-system primitives (Ui*), registered globally
├─ components/domain/       13 AIOps components built from Ui* primitives
├─ components/layout/       AppSidebar, AppTopBar
└─ views/                   19 pages, lazy-loaded per route
```

Dependency rule: **views → domain → ui → tokens**. UI primitives know nothing about AIOps; domain components know
nothing about routing; only views and stores call the API.

### JS library (common functions)

| Module | Used by | What it removes |
|---|---|---|
| `lib/api.js` | 4 stores, 11 views | `fetch` boilerplate, JSON parsing, uniform error handling (`e.status`, `e.code`, `e.details`) |
| `lib/format.js` | 8 views, 7 components | duplicated number/time formatting |
| `lib/vocab.js` | 7 components, 1 view, 1 store | status words and colours living in one place (rename "Needs approval" once) |
| `composables/usePolling.js` | 13 views + App.vue | timers, cleanup on unmount, pausing in background tabs |

### Component library (design system) - measured reuse

| Component | Uses | Files | Purpose |
|---|---|---|---|
| UiButton | 55 | 18 | primary / tint / plain / danger / ghost × sm / md / lg, loading, router link or external |
| UiList + UiListRow | 55 | 15 | iOS inset grouped list with leading tile, title, subtitle, detail, accessory, chevron |
| UiPill | 25 | 11 | status chip, 8 tones |
| UiCard | 20 | 9 | surface with optional title and actions |
| UiPageHeader | 20 | 19 | large title, subtitle, back link, actions |
| UiAppTile | 19 | 14 | logo or icon tile with a status dot |
| UiEmpty / UiField | 13 / 13 | 8 / 7 | empty states; labelled inputs (v-model) |
| UiWait | 11 | 6 | waiting / done box used by connect flows and "AI is investigating" |
| UiLogo / UiIcon | 10 / 7 | 4 / 6 | brand logos; Fluent icons via CSS mask (inherits text colour) |
| UiAreaChart · UiDisclosure | 8 · 8 | 3 · 8 | area chart with peak line; collapsible section |
| UiMeter · UiTile · UiStatusDot · UiSheet | 6 each | 2-5 | bars, KPI tiles, dots, modal / bottom sheet |
| UiSwitch · UiCodeBlock · UiSegmented · UiStepper · UiStars · UiSpinner · UiToastHost | 1-5 | | form controls, copyable code, progress, rating |

Domain components (built only from Ui*): `ServiceRow` (4 views), `ProblemRow` (3), `TraceWaterfall` (3), `StatusPill` (2),
`HostRow`, `SeverityPill`, `DryRunChecklist`, `FixPanel`, `FeedbackCard`, `InvestigationTimeline`, `ServiceMapCanvas`,
`MapSidePanel`, `TestRequestPanel`, `AutoTraceStatus` (Connect a computer + Computer detail: what the eBPF tracer is doing).

### State management (Pinia)

| Store | State | Read by |
|---|---|---|
| `app` | overview: services, discovered, hosts, open problems, KPIs, AI + detector status | sidebar badge, top bar chips, Home, Connect a service (OTLP endpoint) - loaded once by `App.vue` every 15 s and shared |
| `incidents` | list, per-id cache; actions `decide`, `feedback`, `close`, `reanalyze` | Problems, Problem detail, FixPanel, FeedbackCard; approving refreshes `app` so the badge updates everywhere |
| `catalog` | services, hosts, unregistered telemetry; CRUD actions | Services, Computers, Connect flows, detail pages |
| `map` | graph, selected node, filter, test-request life cycle (`sending → tracing → playing → done`) | ServiceMapCanvas, MapSidePanel, TestRequestPanel stay in sync without props drilling |
| `ui` | toasts, mobile drawer, saved preferences (approver name, last owner) | every component that shows feedback |

## Design concepts and evidence

| Concept | Evidence in the code |
|---|---|
| **Design consistency** | Every colour/size comes from `tokens.css`; no page defines its own button or list. The Design System page renders the real components. |
| **Maintenance** | Changing a status label or colour is one line in `vocab.js` / `tokens.css`. The API client is the only place that knows URLs. |
| **Scalability** | New pages are lazy-loaded chunks (Service Map 19 kB, Problem detail 15 kB gzipped ≈ 7 kB / 5 kB); stores are independent. |
| **Faster future development** | A new list page is ~30 lines: `UiPageHeader` + `UiList` + a row component + `usePolling`. The Connect-a-service wizard reuses UiField, UiSegmented, UiCodeBlock, UiWait. |
