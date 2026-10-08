# Vue 3 migration implementation and validation

## Architecture and deployment decision

The Vue application lives in `frontend/` and keeps rendering, API communication, shared state, polling, and formatting separate. FastAPI remains the sole public service on port `8080`; no reverse proxy or new runtime container was added. The `aiops-api` Dockerfile builds Vue in a Node stage and copies only `dist/` to `app/static/vue` in the Python image.

FastAPI serves `/` and all non-API deep links from the Vue entry. `/api`, `/install`, and `/static` retain their existing contracts. The original HTML/CSS/JavaScript frontend remains untouched and is available at `/legacy` until acceptance is complete.

## Screen → API → component mapping

| Route | API integration | Main reusable UI |
|---|---|---|
| `/` | overview | MetricCard, ProblemCard, BasePanel, states |
| `/map` | service map | BasePanel, topology nodes, states |
| `/services` | apps, discovery, app create | BasePanel, BaseInput, BaseButton, table, states |
| `/services/:service` | service detail, traces, app delete | ChartCard, trace dialog, ConfirmDialog, table |
| `/infra` | hosts | host cards, BaseButton, states |
| `/infra/:name` | host detail, host delete | ChartCard, ConfirmDialog, tables |
| `/problems` | incidents | ProblemCard, EmptyState, ErrorState |
| `/problems/:id` | incident detail and all incident actions | BaseBadge, panels, dry-run candidates, approval and feedback forms |
| `/deployments` | deployments | BasePanel, data table |
| `/connect` | static workflow guidance | AppIcon, BasePanel |
| `/connect/service` | app create, discovery, verification | BaseInput, CodeBlock, StatusChip, polling |
| `/connect/computer` | hosts, host create | BaseInput, CodeBlock, polling |
| `/skills` | skills | BaseBadge, BasePanel |
| `/runbooks` | runbooks, toggle | StatusChip, BaseButton, BasePanel |
| `/notifications` | notifications | AppIcon, BasePanel, polling |
| `/chaos` | supported chaos actions and reset | AppIcon, BaseButton, BasePanel |
| `/settings` | settings, save, Teams test | BaseInput, StatusChip, BasePanel |

`AppShell`, `AppSidebar`, `AppTopbar`, `NavItem`, and the Pinia system store are shared by every screen. The centralized HTTP client parses FastAPI error details and the async composable deduplicates overlapping requests, pauses polling while hidden, and clears timers on unmount.

## Validation results

Validated on 2026-10-08:

- `npm run typecheck`: passed.
- `npm test`: passed, 2 files and 3 tests (format contracts and full route inventory).
- `npm run build`: passed; 150 modules transformed and production assets emitted.
- Production dependency audit (`npm audit --omit=dev`): 0 vulnerabilities.
- Python syntax check for `aiops-api/app/main.py`: passed.
- `docker compose config --quiet`: passed.
- Vite history smoke test: all 17 functional routes returned HTTP 200, including both parameterized detail routes and the connect hub.
- Figma comparison: all three pages and their direct child frames/components were inspected. Layout, tokens, components, sidebar assets, and all 15 screen structures were compared during implementation. This was a design-context comparison, not an automated pixel-diff.

## Known limitations and unexecuted checks

- `docker compose build aiops-api` was attempted but could not run because the local Docker daemon was not running. The Compose model still validates successfully.
- A full live-stack E2E run was not executed, so mutations were verified against backend schemas and code paths but not against running Prometheus/Loki/Tempo/Ollama/demo containers.
- Browser automation was unavailable for the local in-app browser. Route serving was checked over HTTP and visual implementation was compared to Figma design context/screenshots, but no automated screenshot-diff artifact was produced.
- The install reports advisories in development-only transitive tooling; the production dependency audit reports zero vulnerabilities. No force upgrade was applied because it would introduce avoidable breaking-version risk.
