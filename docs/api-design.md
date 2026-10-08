# 4. Backend: API Design (Release 1)

FastAPI, base path **`/api/v1`**. Live OpenAPI docs: `http://cp26pt1.sit.kmutt.ac.th:8080/docs`.
Code: [`aiops-api/app/api/`](../aiops-api/app/api) - one router per resource.

## REST principles applied

| Principle | How |
|---|---|
| Resources are nouns, plural | `/services`, `/hosts`, `/incidents`, `/runbooks`, `/deployments`, `/test-requests` |
| Methods carry the meaning | `GET` read · `POST` create (or start a process) · `PUT` idempotent upsert · `PATCH` partial update · `DELETE` remove |
| Sub-resources for things that belong to a parent | `/incidents/{id}/approvals`, `/incidents/{id}/feedback`, `/hosts/{name}/inventory` |
| State changes are resources, not verbs | approving = `POST /incidents/{id}/approvals`; re-running the AI = `POST /incidents/{id}/analyses`; injecting a fault = `POST /scenarios/{id}/runs` |
| Natural keys in URLs where users know them | `/services/payment`, `/hosts/napat-mac`; numeric ids for incidents |
| Long work is asynchronous | `202 Accepted` + `Location` header, then poll (`/test-requests/{id}`, `/incidents/{id}`) |
| Versioned | `/api/v1`; the agent's old `/api/hosts/register` is kept as a hidden alias so installed agents keep working |
| Validation at the edge | Pydantic request models ([`schemas.py`](../aiops-api/app/api/schemas.py)); handlers only see valid input |

## Status codes and error format

Every error has the same body ([`errors.py`](../aiops-api/app/api/errors.py)):

```json
{ "error": { "code": "preflight_failed", "message": "pre-flight dry run failed - nothing was changed",
             "details": { "failed_checks": [{ "name": "target is known-good", "ok": false, "detail": "..." }] } } }
```

| Code | When | Example |
|---|---|---|
| `200 OK` | read / update succeeded | `GET /incidents/12` |
| `201 Created` (+ `Location`) | resource created | `POST /services`, `POST /incidents/12/approvals` |
| `202 Accepted` | work started, poll for the result | `POST /test-requests`, `POST /incidents/12/analyses` |
| `204 No Content` | deleted | `DELETE /services/test` |
| `400 bad_request` | invalid query parameter | `GET /incidents?status=foo` |
| `403 owner_required` | approval without the owner's confirmation | `POST /incidents/12/approvals` with `owner_confirmed=false` |
| `404 not_found` | unknown id/name | `GET /incidents/99999` |
| `409 conflict` | duplicate, or wrong state for the action | approving an incident that is already resolved; `POST /services` for an existing name |
| `422 validation_failed` | body does not match the schema (lists each field) | `{"service_name": "bad name!"}` |
| `422 preflight_failed` | the dry run right before execution failed; nothing was changed | approval of a rollback whose target turned bad |
| `500 internal_error` | unexpected error (logged) | - |
| `503` | `/health` when a dependency (database, Prometheus, LLM) is down | - |

## Endpoints (Release 1 core features)

| Feature | Method & path | Success | Errors |
|---|---|---|---|
| Home dashboard | `GET /overview` | 200 | |
| Platform health | `GET /health` | 200 / 503 | |
| **Connect a service** | `GET /services?kind=` | 200 | |
| | `POST /services` | 201 | 409, 422 |
| | `GET /services/discovered` (sending data, not registered) | 200 | |
| | `GET /services/{name}` | 200 | 404 |
| | `PATCH /services/{name}` | 200 | 404, 422 |
| | `DELETE /services/{name}` | 204 | 404 |
| | `GET /services/{name}/telemetry` (is data arriving?) | 200 | |
| **Connect a computer** | `GET /hosts` | 200 | |
| | `POST /hosts` (node_exporter server) | 201 | 409, 422 |
| | `PUT /hosts/{name}` (agent registration, idempotent) | 200 | 422 |
| | `POST /hosts/{name}/inventory` (agent: processes, containers, connections) | 200 | 404, 422 |
| | `GET /hosts/{name}` | 200 | 404 |
| | `DELETE /hosts/{name}` | 204 | 404 |
| **Service map** | `GET /service-map` | 200 | |
| | `POST /test-requests` | 202 | 409 (no entry point) |
| | `GET /test-requests/{id}` | 200 | 404 |
| | `GET /traces/{trace_id}` | 200 | 404 |
| **Incidents (RCA)** | `GET /incidents?status=open\|closed` | 200 | 400 |
| | `GET /incidents/{id}` | 200 | 404 |
| | `PATCH /incidents/{id}` `{status: closed}` | 200 | 404, 409, 422 |
| | `POST /incidents/{id}/analyses` | 202 | 404, 409 |
| **Owner approval** | `POST /incidents/{id}/approvals` `{decision, candidate_id, approver, owner_confirmed, comment}` | 201 | 403, 404, 409, 422 |
| **Improve score** | `PUT /incidents/{id}/feedback` `{score 1-5, rca_correct, comment}` | 200 | 404, 422 |
| | `GET /runbooks` · `PATCH /runbooks/{id}` `{enabled}` | 200 | 404 |
| | `GET /skills` | 200 | |
| Change tracking (CI) | `GET /deployments` · `POST /deployments` | 200 / 201 | 404, 422 |
| Teams | `GET /notifications` · `POST /notifications/test` | 200 / 201 | |
| Settings | `GET /settings` · `PATCH /settings` | 200 | 422 |
| Demo | `GET /scenarios` · `POST /scenarios/{id}/runs` | 200 / 202 | 404 |

## Example: the approval flow

```
POST /api/v1/incidents/12/approvals
{ "decision": "approve", "candidate_id": 31, "approver": "Napat", "owner_confirmed": true }

-> 403 owner_required        owner_confirmed was false
-> 409 conflict              incident is not waiting for a decision
-> 422 preflight_failed      the dry run is repeated now and failed; nothing changed
-> 201 Created              { ...incident, "status": "verifying", "approval": { "preflight": {...}, "execution": {...} } }
```
