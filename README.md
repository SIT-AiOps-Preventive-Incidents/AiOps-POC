# AIOps One Solution — Agentic AI RCA for Incidents (PoC)

Capstone project PoC: detects incidents from OpenTelemetry data, lets an agent find the root cause with
read-only tools and a small local LLM, dry-runs every fix, and applies it only after the service owner approves.

- Web app: `http://<host>:8080` (Vue 3; all monitoring, RCA, connection, runbook, notification, chaos, and settings workflows)
- Legacy web app during migration acceptance: `http://<host>:8080/legacy`
- Grafana: `http://<host>:3001`
- Architecture answers: [docs/infrastructure-architecture.md](docs/infrastructure-architecture.md)

## Layout

| Path | What |
|---|---|
| `docker-compose.yml` | All 17 containers (obs stack, Ollama, aiops-api, edge firewall/LB, demo shop) |
| `frontend/` | Vue 3 + TypeScript + Vite source, Figma-derived tokens, reusable components, and typed API layer |
| `aiops-api/` | FastAPI app: detector, agent, dry run/remediation, legacy UI, and built Vue static hosting |
| `demo-apps/` | Instrumented demo shop (frontend, checkout, payment, inventory) + load generator |
| `edge/` | nginx configs for the edge firewall and load balancer; `blocklist.conf` is written by owner-approved actions |
| `otel/`, `prometheus/`, `loki/`, `tempo/`, `grafana/` | Observability config |
| `scripts_e2e.sh` | Inject a scenario → wait for RCA → approve → verify |
| `docs/` | Infrastructure answers and the project summary page |

## Run

```bash
docker network create aiops
docker volume create ollama
docker compose build checkout aiops-api      # demo image is shared by all shop services
docker compose up -d
docker exec ollama ollama pull qwen2.5:1.5b
```

Requirements: Docker Engine + Compose v2, ~4 vCPU / 7 GB RAM. No GPU needed.

The `aiops-api` image uses a Node build stage and copies the optimized frontend into the existing Python image. FastAPI still owns port `8080`, `/api`, `/install`, and `/static`; unknown non-API paths return the Vue entry so browser refreshes and deep links work.

## Frontend development

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173; proxies /api and /install to :8080
npm run typecheck
npm test
npm run build
```

The production build uses `/static/vue/` for generated assets. Do not copy `dist/` into source control; Docker builds it. Figma-derived design tokens live in `frontend/src/styles/tokens.css`, and existing repository SVGs are preserved under `frontend/public/icons/`.

Migration audit, route/API/component mapping, validation evidence, and known limitations are in [docs/frontend-migration-audit.md](docs/frontend-migration-audit.md) and [docs/frontend-migration-validation.md](docs/frontend-migration-validation.md).

## Scenarios

`./scripts_e2e.sh <bad_deploy|slow_db|cpu_hog|brute_force|instance_fault>` or the Chaos page in the UI.
`curl -XPOST localhost:8080/api/chaos/reset` clears injected faults and the firewall deny list.
