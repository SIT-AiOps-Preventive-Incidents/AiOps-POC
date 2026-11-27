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
| `aiops-api/` | FastAPI app: REST API v1 (`app/api`), detector, agent (skills, tools, grounding guard), dry run + remediation, host inventory, test requests, PostgreSQL schema (`app/schema.sql`) |
| `frontend/` | Vue 3 + Vite + Pinia web app: design tokens, component library (`components/ui`), domain components, stores, views |
| `demo-apps/` | Instrumented demo shop (frontend, checkout, payment, inventory) + load generator |
| `edge/` | nginx configs for the edge firewall and load balancer; `blocklist.conf` is written by owner-approved actions |
| `otel/`, `prometheus/`, `loki/`, `tempo/`, `grafana/` | Observability config |
| `scripts_e2e.sh` | Inject a scenario → wait for RCA → approve → verify |
| `docs/` | Infrastructure answers, API design, ER diagram (6 views), UX/UI + component design, project summary page |

## Run

```bash
docker network create aiops
docker volume create ollama
docker compose build checkout aiops-api      # aiops-api builds the Vue app in a multi-stage Dockerfile
docker compose up -d
docker exec ollama ollama pull qwen2.5:1.5b
```

Requirements: Docker Engine + Compose v2, ~4 vCPU / 7 GB RAM. No GPU needed.
Frontend dev: `cd frontend && npm install && npm run dev` (proxies `/api` to the VM).
Connect a computer: `curl -fsSL http://<host>:8080/install/agent.sh | AIOPS_HOST_NAME=<name> sh`

## Scenarios

`./scripts_e2e.sh <bad_deploy|slow_db|cpu_hog|brute_force|instance_fault>` or the Chaos page in the UI.
`curl -XPOST localhost:8080/api/chaos/reset` clears injected faults and the firewall deny list.

## Suricata network evidence

Enable the optional passive sensors for the shop on a Linux Docker Engine host.

```bash
export DEMO_DATASET=shop
docker compose --profile suricata up -d --build
bash netlab/up.sh
```

The sensors share the network namespaces of `edge-fw` and `checkout`. The checkout sensor can also see the lab interface added by `netlab/up.sh`. Run this command if you recreate either monitored container separately.

```bash
docker compose --profile suricata up -d --force-recreate suricata-edge suricata-checkout
```

- In Grafana **Explore → Loki**, query `{service_name="suricata"} | json`. To filter by record type, append `| event_type = "flow"` or use `alert`, `dns`, `tls`, or `stats`. Add `service_namespace="edge"` or `service_namespace="checkout"` to the stream selector to inspect one sensor. DNS and TLS records depend on traffic visible at those capture points.
- Wait for both lab cables to show as up in **Network**. Run **Demo scenarios → Network → Uplink cut** and open the resulting checkout or frontend incident in **Problems**. Look for TCP packet counts under **Evidence**. When a sampled flow has outgoing SYN packets with no reverse TCP packets and discovery places the destination behind a down link, the RCA names the link and gives the owner a manual runbook. **Reset everything** restores the port.
- The existing **Password attack** demo can show the edge sensor's login request alert. Suricata reports the packet source, which can be a proxy or the load generator. The application and firewall logs identify the failed attempts and the forwarded client IP. The source of any block recommendation is the existing authentication investigation.
