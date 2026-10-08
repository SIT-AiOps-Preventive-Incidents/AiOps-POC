# Vue 3 frontend migration audit

## Sources and branch safety

- Functional baseline: `origin/dev` at `4fda663` (`feat: light iOS/Azure UI, one-command host agent, guided connect, real icons`).
- Working branch: `feature/frontend-vue3`, created directly from the fetched `origin/dev`.
- Visual baseline: Figma file `BqeAEvLhkIEHXAHajD8t8p`.
- The legacy frontend remains in `aiops-api/app/static/` until Vue feature parity is validated.

## Figma inventory

All three Figma pages were inspected, including their top-level children and the 15 desktop frame screenshots.

### 00 · Foundations

- Surfaces: `#F5F6FB` default/sunken, `#FFFFFF` surface/raised.
- Text: `#172033` default, `#667085` muted, `#98A2B3` dim.
- Borders: `#E7EAF1` default, `#D0D5DD` strong.
- Accents: `#1496FF` primary, `#9B5CFF` AI, `#00B4C5` tertiary, `#F5C542` highlight.
- Status: `#22B66F` success, `#F59E0B` warning, `#F0445E` danger.
- Typography: Inter; 32/40 display, 24/32 h1, 18/26 h2, 16/24 large body, 14/20 body, 12/18 small/code, 11/16 label.
- Layout: 240 px foundation guidance; VM-aligned page frames use a 184 px sidebar, 56 px top bar, 24–28 px page gutters, 12–16 px gaps, and 6–10 px radii.

### 01 · Components Design

- Button: Primary, Secondary, Danger; Default and Disabled.
- Badge: Success, Warning, Danger, Info, AI, Neutral semantic pairs.
- Nav Item: Default and Active.
- Input: Default, Focus, Disabled.
- Metric Card, Panel, Data Row (Default/Hover), Status Chip, Chart Card.
- Problem Card: Awaiting Approval and Fix Failed.
- Twelve VM outline icons, twelve VM nav variants, and twelve full-height sidebar variants.
- The repository's SVGs are the implementation source; no icon library substitutions are allowed.

### 02 · Page Design

| Figma frame | Route | Primary live data |
|---|---|---|
| Overview | `/` | overview KPI, services, hosts, open incidents, topology summary |
| Service Map | `/map` | service map and topology |
| Services | `/services` | connected apps and telemetry discovery |
| Service Detail | `/services/:service` | health, series, endpoints, versions, traces, logs, deployments |
| Infrastructure | `/infra` | hosts and health |
| Host Detail | `/infra/:name` | host series, processes, containers, incidents |
| Problems | `/problems` | incidents |
| Deployments | `/deployments` | deployments |
| Connect App | `/connect/service` | app create, discovery endpoint, telemetry verification |
| Connect Infrastructure | `/connect/computer` | host create/register/polling |
| Skills & Scoring | `/skills` | skill performance and lessons |
| Runbook Memory | `/runbooks` | runbooks and enable/disable action |
| Notifications | `/notifications` | notification delivery history |
| Chaos Scenarios | `/chaos` | chaos actions |
| Settings | `/settings` | settings, model status, Teams test |

The Figma screens contain representative content only. Production views must render real API values and preserve empty/loading/error states.

## Existing frontend feature inventory

### Routing and navigation

- Hash-router routes for overview, problems, problem detail, service map, services, service detail, infrastructure, host detail, connect hub/service/computer, deployments, skills, runbooks, notifications, chaos, and settings.
- Legacy aliases `#/connect/app` and `#/connect/infra` redirect to the connect hub.
- Sidebar open-problem badge and global detector/LLM/Grafana status.

### Polling

- Overview 10 s; problems 6 s; incident detail 4 s.
- Service map 15 s; services 10 s; service detail 15 s.
- Infrastructure 10 s; host detail 15 s; notifications 10 s; deployments 15 s.
- Connect computer 3 s and connect service verification 4 s while relevant.
- Global overview status refresh 20 s outside the overview route.
- Polling pauses for hidden documents; route timers are cleaned up on navigation.
- Incident detail avoids replacement while a form control is focused and preserves form/details state.

### Mutations and validation

- Add discovered service with owner; create a service from the guided flow; delete a service with confirmation.
- Add a node_exporter host after non-empty name/address validation; agent registration is polled; delete a host with confirmation.
- Approval requires a non-empty approver, owner confirmation, and a successful dry run. Candidate actions that failed dry-run checks are disabled.
- Reject supports approver/comment; close and reanalyze are available according to incident status.
- Feedback requires a 1–5 rating and includes RCA correctness and a learning comment.
- Toggle runbooks, execute/reset chaos scenarios, save settings, and save-then-test Microsoft Teams.
- Copy installation/instrumentation snippets with a selection fallback when Clipboard API access fails.
- Trace waterfall modal, Escape/backdrop modal close, toasts, responsive navigation, and loading/error/empty states.

## API contract map

Interfaces must follow these backend-returned shapes; optional values reflect telemetry or empty database states.

| Area | Calls | Key contract notes |
|---|---|---|
| Global/overview | `GET /api/overview` | services, hosts, open problems, KPI, detector, LLM and Grafana URL |
| Map | `GET /api/servicemap`, `GET /api/topology` | nodes, edges, entry nodes, hosts, sampled traces; topology returns `{from,to,count}` |
| Services | `GET/POST /api/apps`, `DELETE /api/apps/{id}` | create accepts `AppIn`; duplicate `service_name` returns 409 |
| Service detail | `GET /api/services/{svc}` | app, health, time series, endpoints, versions, deployments, logs, traces, outbound RPS, incidents |
| Verification/discovery | `GET /api/apps/{svc}/verify`, `GET /api/discover` | metrics/logs/traces flags; unconnected services/hosts and public endpoints |
| Infrastructure | `GET/POST /api/hosts`, `POST /api/hosts/register`, `GET /api/hosts/{name}`, `DELETE /api/hosts/{id}` | host create requires name/address; detail includes series, processes, containers, incidents |
| Traces | `GET /api/traces/{id}` | span timing tree used by the trace modal |
| Incidents | `GET /api/incidents`, `GET /api/incidents/{id}` | decoded JSON evidence, steps, candidates, action, dry-run and execution fields |
| Incident actions | approve/reject/close/reanalyze/feedback | approval body includes approver, candidate index, comment, owner confirmation; feedback is clamped to 1–5 |
| Deployments | `GET/POST /api/deployments` | POST accepts service, version, commit, author, message, optional profile |
| Skills/runbooks | `GET /api/skills`, `GET /api/runbooks`, `POST /api/runbooks/{id}/toggle` | live aggregates and stored runbook memory |
| Notifications/settings | `GET /api/notifications`, `GET/PUT /api/settings`, `POST /api/settings/test-teams` | settings are string-valued and only known keys persist |
| Chaos | `POST /api/chaos/{scenario}` | supported: bad_deploy, slow_db, cpu_hog, brute_force, instance_fault, reset |

## Design/API gaps and decisions

- Figma shows static example values; every Vue screen will render backend data and retain legacy actions even when the mockup omits them.
- Figma Connect screens resemble one-page forms while the legacy UI contains guided flows, runtime-specific snippets, verification polling, and copy actions. The functionality is retained in the Figma visual language.
- Figma Settings includes a destructive-action approval switch not represented by a persisted backend key. It will be presented as a non-editable safety guardrail instead of inventing an API field.
- Figma includes a sixth slow-dependency example, but the backend exposes only the five named scenarios plus reset. No unsupported scenario will be sent.
- The legacy `/api/traces/{id}` call is preserved even though it was not listed in the requested endpoint summary because the trace modal depends on the implemented backend route.
- Vue production output is served by FastAPI at the existing port and origin. A catch-all returns the Vue entry for deep links while `/api`, `/install`, and `/static` keep their existing behavior.
- The legacy assets remain available at `/legacy` during verification. Docker builds Vue in a Node stage and copies only the production output into the Python image, minimizing impact on other services.

## Implementation sequence

1. Scaffold Vue 3, TypeScript, Vite, Router, Pinia, Tailwind, Chart.js, and test tooling.
2. Implement Figma tokens, shell, icons, core components, request client, typed contracts, polling, notifications, and dialogs.
3. Migrate monitoring, topology, services, infrastructure, incidents/RCA, connection flows, operations, and settings.
4. Add FastAPI SPA/deep-link serving and the multi-stage Docker build while retaining the legacy frontend.
5. Typecheck, unit-test critical state/formatting behavior, build, smoke-test all routes, exercise available API calls, run Docker validation, and compare rendered screenshots to Figma.

Implementation and verification results are tracked in [frontend-migration-validation.md](frontend-migration-validation.md).
