# AIOps One Solution — Agentic AI RCA for Incidents (PoC)

Capstone project PoC: detects incidents from OpenTelemetry data, lets an agent find the root cause with
read-only tools and a small local LLM, dry-runs every fix, and applies it only after the service owner approves.

- Web app: `http://<host>:8080` (Overview, Service Map, Services, Infrastructure, Problems, Connect App/Infra, Chaos)
- Grafana: `http://<host>:3001`
- Architecture answers: [docs/infrastructure-architecture.md](docs/infrastructure-architecture.md)

## Layout

| Path | What |
|---|---|
| `docker-compose.yml` | All 17 containers (obs stack, Ollama, aiops-api, edge firewall/LB, demo shop) |
| `aiops-api/` | FastAPI app: detector, agent (skills, tools, grounding guard), dry run + remediation, UI (`app/static`) |
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

## Scenarios

`./scripts_e2e.sh <bad_deploy|slow_db|cpu_hog|brute_force|instance_fault>` or the Chaos page in the UI.
`curl -XPOST localhost:8080/api/chaos/reset` clears injected faults and the firewall deny list.
