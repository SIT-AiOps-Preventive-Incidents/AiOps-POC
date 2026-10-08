-- AIOps One - PostgreSQL schema (normalized). Idempotent: safe to run on every start.
-- Entities: teams, hosts, services, service_instances, connections, deployments,
--           skills, skill_tools, incidents (+ affected services, evidence, runbook steps, agent steps),
--           remediation_candidates, dry_runs (+ checks, changes), approvals, executions,
--           feedback, runbooks (+ steps), notifications, settings.

CREATE TABLE IF NOT EXISTS teams (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  contact     TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hosts (
  id           SERIAL PRIMARY KEY,
  name         TEXT NOT NULL UNIQUE,
  address      TEXT NOT NULL DEFAULT '',
  os           TEXT NOT NULL DEFAULT '',
  arch         TEXT NOT NULL DEFAULT '',
  agent        TEXT NOT NULL DEFAULT 'aiops-agent' CHECK (agent IN ('aiops-agent', 'node_exporter')),
  kind         TEXT NOT NULL DEFAULT 'server' CHECK (kind IN ('server', 'workstation')),
  environment  TEXT NOT NULL DEFAULT 'production',
  ip_addresses TEXT[] NOT NULL DEFAULT '{}',
  team_id      INT REFERENCES teams(id) ON DELETE SET NULL,
  last_inventory_at TIMESTAMPTZ,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS services (
  id           SERIAL PRIMARY KEY,
  service_name TEXT NOT NULL UNIQUE,           -- OpenTelemetry service.name, or "<process>-<port>" when discovered
  display_name TEXT NOT NULL,
  kind         TEXT NOT NULL DEFAULT 'service' CHECK (kind IN ('service', 'network', 'process', 'external')),
  source       TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'traced', 'discovered')),
  language     TEXT,
  team_id      INT REFERENCES teams(id) ON DELETE SET NULL,
  repo         TEXT NOT NULL DEFAULT '',
  environment  TEXT NOT NULL DEFAULT 'production',
  admin_urls   TEXT[] NOT NULL DEFAULT '{}',     -- runtime control endpoints (rollback) - demo apps only
  entry_url    TEXT,                             -- where a test request enters (service map "Test request")
  entry_method TEXT NOT NULL DEFAULT 'GET',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS service_instances (
  id           SERIAL PRIMARY KEY,
  service_id   INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  host_id      INT REFERENCES hosts(id) ON DELETE CASCADE,
  name         TEXT NOT NULL,                    -- container name, OTel service.instance.id or "<process>:<pid>"
  container    TEXT,
  pid          INT,
  port         INT,
  last_seen    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (service_id, name)
);

-- Network flows observed by the host agent (who talks to whom), used when a service is not traced.
CREATE TABLE IF NOT EXISTS connections (
  id               SERIAL PRIMARY KEY,
  src_service_id   INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  dst_service_id   INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  observed_by      INT REFERENCES hosts(id) ON DELETE CASCADE,
  samples          INT NOT NULL DEFAULT 1,
  last_seen        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (src_service_id, dst_service_id)
);

CREATE TABLE IF NOT EXISTS deployments (
  id           SERIAL PRIMARY KEY,
  service_id   INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  version      TEXT NOT NULL,
  commit_hash  TEXT NOT NULL,
  author       TEXT NOT NULL DEFAULT '',
  message      TEXT NOT NULL DEFAULT '',
  profile      TEXT NOT NULL DEFAULT 'healthy',
  deployed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deployments_service_time ON deployments (service_id, deployed_at DESC);

CREATE TABLE IF NOT EXISTS skills (
  id          TEXT PRIMARY KEY,                  -- e.g. service-error-analysis
  name        TEXT NOT NULL,
  category    TEXT NOT NULL,
  description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS skill_tools (
  skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
  seq         INT NOT NULL,
  tool        TEXT NOT NULL,
  PRIMARY KEY (skill_id, seq)
);

CREATE TABLE IF NOT EXISTS runbooks (
  id                 SERIAL PRIMARY KEY,
  signature          TEXT NOT NULL UNIQUE,      -- kind|service|action
  title              TEXT NOT NULL,
  kind               TEXT NOT NULL,
  skill_id           TEXT REFERENCES skills(id),
  root_cause         TEXT NOT NULL DEFAULT '',
  action_type        TEXT NOT NULL,
  action_params      JSONB NOT NULL DEFAULT '{}',
  uses               INT NOT NULL DEFAULT 0,
  enabled            BOOLEAN NOT NULL DEFAULT true,
  source_incident_id INT,                        -- FK added below (circular with incidents)
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS runbook_steps (
  runbook_id  INT NOT NULL REFERENCES runbooks(id) ON DELETE CASCADE,
  seq         INT NOT NULL,
  text        TEXT NOT NULL,
  PRIMARY KEY (runbook_id, seq)
);

CREATE TABLE IF NOT EXISTS incidents (
  id            SERIAL PRIMARY KEY,
  title         TEXT NOT NULL,
  kind          TEXT NOT NULL,                   -- error_rate | latency | host_cpu | host_mem | host_disk | host_down | auth_bruteforce
  severity      TEXT NOT NULL CHECK (severity IN ('critical', 'major', 'minor')),
  status        TEXT NOT NULL CHECK (status IN ('open', 'analyzing', 'awaiting_approval', 'remediating',
                                                'verifying', 'resolved', 'rejected', 'closed', 'remediation_failed')),
  entity_type   TEXT NOT NULL CHECK (entity_type IN ('service', 'host')),
  service_id    INT REFERENCES services(id) ON DELETE SET NULL,
  host_id       INT REFERENCES hosts(id) ON DELETE SET NULL,
  entity_name   TEXT NOT NULL,                   -- kept so history survives deleting the entity
  owner_team_id INT REFERENCES teams(id) ON DELETE SET NULL,
  signal        JSONB NOT NULL DEFAULT '{}',     -- detector reading at detection time (value, threshold, baseline, by_version)
  facts         JSONB NOT NULL DEFAULT '{}',     -- correlated evidence the agent produced
  skill_id      TEXT REFERENCES skills(id),
  skill_reason  TEXT,
  path          TEXT CHECK (path IN ('new', 'known')),
  root_cause    TEXT,
  summary       TEXT,
  confidence    NUMERIC(4,3),
  llm_model     TEXT,
  llm_ok        BOOLEAN,
  analysis_ms   INT,
  runbook_id    INT REFERENCES runbooks(id) ON DELETE SET NULL,
  started_at    TIMESTAMPTZ NOT NULL,
  detected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  analyzed_at   TIMESTAMPTZ,
  resolved_at   TIMESTAMPTZ,
  CHECK (service_id IS NULL OR host_id IS NULL)
);
CREATE INDEX IF NOT EXISTS incidents_status ON incidents (status, detected_at DESC);
DO $$ BEGIN
  ALTER TABLE runbooks ADD CONSTRAINT runbooks_source_incident_fk
    FOREIGN KEY (source_incident_id) REFERENCES incidents(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE TABLE IF NOT EXISTS incident_affected_services (
  incident_id INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  service_id  INT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
  PRIMARY KEY (incident_id, service_id)
);
CREATE TABLE IF NOT EXISTS incident_evidence (
  incident_id INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  seq         INT NOT NULL,
  text        TEXT NOT NULL,
  PRIMARY KEY (incident_id, seq)
);
CREATE TABLE IF NOT EXISTS incident_runbook_steps (
  incident_id INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  seq         INT NOT NULL,
  text        TEXT NOT NULL,
  PRIMARY KEY (incident_id, seq)
);
CREATE TABLE IF NOT EXISTS agent_steps (
  id           SERIAL PRIMARY KEY,
  incident_id  INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  seq          INT NOT NULL,
  kind         TEXT NOT NULL,                    -- info | llm | skill | tool | analysis | memory | dryrun | guard | done
  title        TEXT NOT NULL,
  detail       TEXT,
  data         JSONB NOT NULL DEFAULT '{}',      -- tool args/output, llm meta/output, checks ...
  duration_ms  INT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (incident_id, seq)
);

CREATE TABLE IF NOT EXISTS remediation_candidates (
  id           SERIAL PRIMARY KEY,
  incident_id  INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  rank         INT NOT NULL,                     -- 0 = recommended
  action_type  TEXT NOT NULL CHECK (action_type IN ('rollback_deployment', 'restart_service', 'restart_instance',
                                                     'block_ip', 'manual')),
  params       JSONB NOT NULL DEFAULT '{}',
  label        TEXT NOT NULL,
  UNIQUE (incident_id, rank)
);
CREATE TABLE IF NOT EXISTS dry_runs (
  id           SERIAL PRIMARY KEY,
  candidate_id INT NOT NULL REFERENCES remediation_candidates(id) ON DELETE CASCADE,
  phase        TEXT NOT NULL CHECK (phase IN ('proposal', 'preflight')),
  ok           BOOLEAN NOT NULL,
  impact       TEXT NOT NULL DEFAULT '',
  ran_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS dry_run_checks (
  dry_run_id  INT NOT NULL REFERENCES dry_runs(id) ON DELETE CASCADE,
  seq         INT NOT NULL,
  name        TEXT NOT NULL,
  ok          BOOLEAN NOT NULL,
  detail      TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (dry_run_id, seq)
);
CREATE TABLE IF NOT EXISTS dry_run_changes (
  dry_run_id  INT NOT NULL REFERENCES dry_runs(id) ON DELETE CASCADE,
  seq         INT NOT NULL,
  change      TEXT NOT NULL,
  PRIMARY KEY (dry_run_id, seq)
);

CREATE TABLE IF NOT EXISTS approvals (
  id            SERIAL PRIMARY KEY,
  incident_id   INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  candidate_id  INT REFERENCES remediation_candidates(id) ON DELETE SET NULL,
  decision      TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
  approver      TEXT NOT NULL,
  owner_team_id INT REFERENCES teams(id) ON DELETE SET NULL,
  comment       TEXT NOT NULL DEFAULT '',
  preflight_id  INT REFERENCES dry_runs(id) ON DELETE SET NULL,
  decided_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS executions (
  id            SERIAL PRIMARY KEY,
  approval_id   INT NOT NULL UNIQUE REFERENCES approvals(id) ON DELETE CASCADE,
  ok            BOOLEAN NOT NULL,
  detail        TEXT NOT NULL DEFAULT '',
  executed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  verified      BOOLEAN,
  verify_attempts INT,
  verified_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS feedback (
  id           SERIAL PRIMARY KEY,
  incident_id  INT NOT NULL UNIQUE REFERENCES incidents(id) ON DELETE CASCADE,
  score        INT NOT NULL CHECK (score BETWEEN 1 AND 5),
  rca_correct  BOOLEAN NOT NULL DEFAULT true,
  comment      TEXT NOT NULL DEFAULT '',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notifications (
  id           SERIAL PRIMARY KEY,
  incident_id  INT REFERENCES incidents(id) ON DELETE CASCADE,
  channel      TEXT NOT NULL DEFAULT 'teams',
  event        TEXT NOT NULL,
  status       TEXT NOT NULL,
  payload      JSONB NOT NULL DEFAULT '{}',
  sent_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS settings (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL
);

-- Release 1.1: automatic (eBPF) instrumentation. How a service is traced, and what the host's agent reports about it.
ALTER TABLE services ADD COLUMN IF NOT EXISTS instrumentation TEXT;   -- NULL = not traced, 'sdk' = OpenTelemetry SDK, 'ebpf' = traced by the host agent
ALTER TABLE hosts    ADD COLUMN IF NOT EXISTS auto_instrument JSONB;  -- last eBPF status from the agent: {state, services, error, version}
