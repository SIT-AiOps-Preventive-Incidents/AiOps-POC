# 5. Conceptual DB Design - ER Diagram (Release 1)

PostgreSQL 17, schema in [`aiops-api/app/schema.sql`](../aiops-api/app/schema.sql). The design is product-neutral:
every entity, attribute and relationship below maps 1:1 to a relational table or to a document collection.
Crow's-foot notation; the model is split into six views so no relationship lines cross. Entities that
appear in more than one view (TEAM, SERVICE, HOST, INCIDENT) are the same table, shown with only the keys the view needs.

Each view is also rendered as an SVG next to this file.

### 5.1 Services, hosts and deployments

![5.1 Services, hosts and deployments](er-1-inventory.svg)

```mermaid
erDiagram
  TEAM ||--o{ SERVICE : owns
  TEAM ||--o{ HOST : owns
  SERVICE ||--o{ DEPLOYMENT : "is deployed as"
  SERVICE ||--o{ SERVICE_INSTANCE : has
  HOST ||--o{ SERVICE_INSTANCE : runs
  TEAM {
    int id PK
    text name UK
    text contact
  }
  SERVICE {
    int id PK
    text service_name UK "OTel service.name"
    text display_name
    text kind "service, network, process, external"
    text source "manual, traced, discovered"
    text language
    int team_id FK
    text_array admin_urls
    text entry_url "test request entry"
  }
  HOST {
    int id PK
    text name UK
    text os
    text agent "aiops-agent, node_exporter"
    text kind "server, workstation"
    text_array ip_addresses
    int team_id FK
    timestamptz last_inventory_at
  }
  DEPLOYMENT {
    int id PK
    int service_id FK
    text version
    text commit_hash
    text author
    timestamptz deployed_at
  }
  SERVICE_INSTANCE {
    int id PK
    int service_id FK
    int host_id FK
    text name
    text container
    int pid
    int port
    timestamptz last_seen
  }
```

### 5.2 Network topology seen by host agents

![5.2 Network topology seen by host agents](er-2-network.svg)

```mermaid
erDiagram
  SERVICE ||--o{ CONNECTION : "calls (src)"
  SERVICE ||--o{ CONNECTION : "is called (dst)"
  HOST ||--o{ CONNECTION : observes
  SERVICE {
    int id PK
    text service_name UK "OTel service.name"
  }
  CONNECTION {
    int id PK
    int src_service_id FK
    int dst_service_id FK
    int observed_by FK
    int samples
    timestamptz last_seen
  }
  HOST {
    int id PK
    text name UK
  }
```

### 5.3 Incident context - who owns it, what it is about, which skill investigates

![5.3 Incident context - who owns it, what it is about, which skill investigates](er-3-context.svg)

```mermaid
erDiagram
  SKILL ||--|{ SKILL_TOOL : uses
  SKILL ||--o{ INCIDENT : investigates
  TEAM ||--o{ INCIDENT : "approves fixes for"
  HOST |o--o{ INCIDENT : "is the entity of"
  SERVICE |o--o{ INCIDENT : "is the entity of"
  INCIDENT ||--o{ INCIDENT_AFFECTED_SERVICE : "also affects"
  SERVICE ||--o{ INCIDENT_AFFECTED_SERVICE : "is affected by"
  SKILL {
    text id PK
    text name
    text category
    text description
  }
  SKILL_TOOL {
    text skill_id PK
    int seq PK
    text tool
  }
  TEAM {
    int id PK
    text name UK
  }
  HOST {
    int id PK
    text name UK
  }
  SERVICE {
    int id PK
    text service_name UK "OTel service.name"
  }
  INCIDENT {
    int id PK
    int service_id FK
    int host_id FK
    int owner_team_id FK
    text skill_id FK
  }
  INCIDENT_AFFECTED_SERVICE {
    int incident_id PK
    int service_id PK
  }
```

### 5.4 Incident and what the AI found

![5.4 Incident and what the AI found](er-4-incident.svg)

```mermaid
erDiagram
  INCIDENT ||--o{ AGENT_STEP : "investigated in"
  INCIDENT ||--o{ INCIDENT_EVIDENCE : "explained by"
  INCIDENT ||--o{ NOTIFICATION : "announced by"
  INCIDENT {
    int id PK
    text title
    text kind
    text severity "critical, major, minor"
    text status
    text entity_type "service, host"
    int service_id FK
    int host_id FK
    text entity_name
    int owner_team_id FK
    text skill_id FK
    int runbook_id FK
    jsonb signal
    jsonb facts
    text root_cause
    text summary
    numeric confidence
    text path "new, known"
    timestamptz started_at
    timestamptz detected_at
    timestamptz analyzed_at
    timestamptz resolved_at
  }
  AGENT_STEP {
    int id PK
    int incident_id FK
    int seq
    text kind "tool, llm, skill, dryrun, guard"
    text title
    jsonb data
    int duration_ms
  }
  INCIDENT_EVIDENCE {
    int incident_id PK
    int seq PK
    text text
  }
  NOTIFICATION {
    int id PK
    int incident_id FK
    text channel
    text event
    text status
    timestamptz sent_at
  }
```

### 5.5 Fix and owner approval

![5.5 Fix and owner approval](er-5-fix.svg)

```mermaid
erDiagram
  INCIDENT ||--|{ REMEDIATION_CANDIDATE : proposes
  INCIDENT ||--o{ APPROVAL : "decided by"
  REMEDIATION_CANDIDATE ||--|{ DRY_RUN : "checked by"
  REMEDIATION_CANDIDATE |o--o{ APPROVAL : "chosen in"
  DRY_RUN |o--o| APPROVAL : "pre-flight of"
  DRY_RUN ||--|{ DRY_RUN_CHECK : contains
  DRY_RUN ||--o{ DRY_RUN_CHANGE : "would make"
  APPROVAL ||--o| EXECUTION : triggers
  INCIDENT {
    int id PK
    int runbook_id FK
  }
  REMEDIATION_CANDIDATE {
    int id PK
    int incident_id FK
    int rank "0 = recommended"
    text action_type
    jsonb params
    text label
  }
  APPROVAL {
    int id PK
    int incident_id FK
    int candidate_id FK
    int preflight_id FK
    text decision "approved, rejected"
    text approver
    int owner_team_id FK
    timestamptz decided_at
  }
  DRY_RUN {
    int id PK
    int candidate_id FK
    text phase "proposal, preflight"
    bool ok
    text impact
    timestamptz ran_at
  }
  DRY_RUN_CHECK {
    int dry_run_id PK
    int seq PK
    text name
    bool ok
    text detail
  }
  DRY_RUN_CHANGE {
    int dry_run_id PK
    int seq PK
    text change
  }
  EXECUTION {
    int id PK
    int approval_id FK
    bool ok
    text detail
    bool verified
    int verify_attempts
  }
```

### 5.6 Learning - feedback and runbook memory

![5.6 Learning - feedback and runbook memory](er-6-learning.svg)

```mermaid
erDiagram
  INCIDENT ||--o| FEEDBACK : "rated by"
  INCIDENT ||--o{ INCIDENT_RUNBOOK_STEP : "fixed by"
  RUNBOOK |o--o{ INCIDENT : "reused by"
  RUNBOOK ||--|{ RUNBOOK_STEP : contains
  INCIDENT {
    int id PK
    int runbook_id FK
  }
  FEEDBACK {
    int id PK
    int incident_id FK
    int score "1 to 5"
    bool rca_correct
    text comment
  }
  INCIDENT_RUNBOOK_STEP {
    int incident_id PK
    int seq PK
    text text
  }
  RUNBOOK {
    int id PK
    text signature UK "kind, service, action"
    text title
    text action_type
    jsonb action_params
    int uses
    bool enabled
    int source_incident_id FK
  }
  RUNBOOK_STEP {
    int runbook_id PK
    int seq PK
    text text
  }
```

## Why it is shaped this way

| Decision | Reason |
|---|---|
| **M:N "incident also affects services" resolved with INCIDENT_AFFECTED_SERVICE** | An associative entity instead of a many-to-many line, as in a normalized relational design. |
| **Incident is the aggregate root**; evidence, runbook steps, agent steps, candidates, approvals, feedback hang off it | One incident page = one aggregate. Everything is deleted with the incident (`ON DELETE CASCADE`). |
| **Dry run is its own entity with checks and changes as child rows** | The same candidate is dry-run twice (`proposal` by the agent, `preflight` right before execution); auditors can see both and compare. |
| **Approval → Execution (1:0..1)** | A rejection has no execution; an approval always records what was run and whether it was verified. |
| **Owner is a Team, referenced from Service, Host and Incident** | Ownership is copied onto the incident at analysis time, so history stays correct if a service later changes owner. |
| **`entity_name` kept on Incident besides the FK** | The FK is `SET NULL` when a service is deleted; the incident still says what it was about. |
| **Service kinds `service / network / process / external`, source `manual / traced / discovered`** | Traced apps, network devices, processes found by the host agent and external databases all share the map, the health checks and the incidents. |
| **Connection (service → service) observed by a Host** | Lines on the service map for apps that do not run OpenTelemetry yet. |
| **Runbook score is derived, not stored** | Average of `FEEDBACK.score` over incidents that reused the runbook: no counters to drift. |
| **`signal`, `facts`, `params`, `data` are JSONB** | They are snapshots whose shape depends on the skill/action (evidence of what the AI saw), not data we query by column. |
| **Metrics, logs and traces are not in this database** | They live in Prometheus, Loki and Tempo; the database keeps only decisions and their evidence. |

Release 2-3 candidates (not built): `USER` + `TEAM_MEMBER` for real owner sign-in (replaces the owner switch), `SILENCE` / maintenance windows, `SLO` per service.
