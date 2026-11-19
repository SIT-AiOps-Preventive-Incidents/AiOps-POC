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
  agent        TEXT NOT NULL DEFAULT 'aiops-agent' CHECK (agent IN ('aiops-agent', 'node_exporter', 'anomod-replay')),
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

-- Release 1.2: servers connected from the platform over SSH. AIOps signs in once with the user's password or key,
-- then keeps a data channel open with its own key (limited to two loopback ports). host_key = the server's SSH key
-- seen on first contact, checked on every reconnect. No password or user key is ever stored.
CREATE TABLE IF NOT EXISTS ssh_links (
  host_name    TEXT PRIMARY KEY,
  address      TEXT NOT NULL,
  port         INT  NOT NULL DEFAULT 22,
  username     TEXT NOT NULL,
  host_key     TEXT NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_connected_at TIMESTAMPTZ
);

-- Release 1.3: "Remove agent" from the web page. Set when someone asks; the agent removes itself on its next
-- report (collector, eBPF tracer, autostart, the platform key) and then the host row is deleted.
ALTER TABLE hosts ADD COLUMN IF NOT EXISTS uninstall_requested_at TIMESTAMPTZ;

-- Release 1.4: "Your network". Segments each connected server sits on, and the neighbours its passive watcher heard
-- over ARP (nothing is scanned). talks_with = processes on the server that had a connection to the neighbour.
CREATE TABLE IF NOT EXISTS net_segments (
  cidr       TEXT NOT NULL,
  host_name  TEXT NOT NULL,
  iface      TEXT NOT NULL DEFAULT '',
  gateway    TEXT,
  last_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cidr, host_name)
);
CREATE TABLE IF NOT EXISTS net_neighbors (
  cidr       TEXT NOT NULL,
  ip         TEXT NOT NULL,
  mac        TEXT,
  name       TEXT,
  seen_by    TEXT,
  talks_with TEXT[] NOT NULL DEFAULT '{}',
  first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (cidr, ip)
);

-- Release 1.4: each replayed AnoMod service sits on its own stand-in machine (agent 'anomod-replay', no host metrics).
ALTER TABLE hosts DROP CONSTRAINT IF EXISTS hosts_agent_check;
ALTER TABLE hosts ADD CONSTRAINT hosts_agent_check CHECK (agent IN ('aiops-agent', 'node_exporter', 'anomod-replay'));

-- Release 2: cloud inventory. A customer's cloud account (read-only credential, sealed), every instance it lists,
-- and what changed between reads. Instances are kept after deletion (gone_at) so the Fleet keeps its history.
CREATE TABLE IF NOT EXISTS cloud_accounts (
  id            SERIAL PRIMARY KEY,
  provider      TEXT NOT NULL CHECK (provider IN ('proxmox', 'openstack', 'vcd', 'cloudstack', 'aws', 'azure', 'gcp')),
  name          TEXT NOT NULL UNIQUE,
  config        JSONB NOT NULL DEFAULT '{}',     -- endpoint, region, project: nothing secret
  secret        TEXT NOT NULL,                   -- Fernet-sealed credential, never returned by the API
  status        TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'ok', 'error')),
  last_sync_at  TIMESTAMPTZ,
  last_error    TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS cloud_instances (
  account_id    INT NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  instance_id   TEXT NOT NULL,
  name          TEXT NOT NULL,
  state         TEXT NOT NULL,                   -- running | stopped | starting | stopping | error | deleted | unknown
  private_ips   TEXT[] NOT NULL DEFAULT '{}',
  public_ips    TEXT[] NOT NULL DEFAULT '{}',
  networks      TEXT[] NOT NULL DEFAULT '{}',
  zone          TEXT,
  size          TEXT,
  created_at    TIMESTAMPTZ,                     -- when the provider created it
  tags          JSONB NOT NULL DEFAULT '{}',
  first_seen    TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen     TIMESTAMPTZ NOT NULL DEFAULT now(),
  gone_at       TIMESTAMPTZ,                     -- no longer listed by the provider
  PRIMARY KEY (account_id, instance_id)
);
CREATE TABLE IF NOT EXISTS cloud_events (
  id            SERIAL PRIMARY KEY,
  account_id    INT NOT NULL REFERENCES cloud_accounts(id) ON DELETE CASCADE,
  ts            TIMESTAMPTZ NOT NULL DEFAULT now(),
  kind          TEXT NOT NULL CHECK (kind IN ('added', 'removed', 'state')),
  instance_id   TEXT NOT NULL,
  name          TEXT NOT NULL,
  detail        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS cloud_events_ts ON cloud_events (ts DESC);

-- Release 2: automation people write themselves. Built-in skills keep their code; a team can switch any skill off,
-- add instructions, or write its own skill (kinds + read-only tools + instructions). Skill sets scope skills to part
-- of the estate. Runbooks can be written by hand (authored), not only learned. Playbooks route and escalate.
ALTER TABLE skills ADD COLUMN IF NOT EXISTS builtin BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE skills ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE skills ADD COLUMN IF NOT EXISTS kinds TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE skills ADD COLUMN IF NOT EXISTS instructions TEXT NOT NULL DEFAULT '';
CREATE TABLE IF NOT EXISTS skill_sets (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL UNIQUE,
  scope       TEXT NOT NULL DEFAULT '',          -- service/host name patterns, comma separated (pay-*, checkout)
  skills      TEXT[] NOT NULL DEFAULT '{}',
  enabled     BOOLEAN NOT NULL DEFAULT true,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE runbooks ADD COLUMN IF NOT EXISTS authored BOOLEAN NOT NULL DEFAULT false;
CREATE TABLE IF NOT EXISTS playbooks (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  enabled     BOOLEAN NOT NULL DEFAULT true,
  trigger     JSONB NOT NULL DEFAULT '{}',       -- {kinds:[], min_severity, entity}
  actions     JSONB NOT NULL DEFAULT '{}',       -- {owner_team, escalate_after_min}; never applies a fix
  runs        INT NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS playbook_escalations (
  incident_id INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  playbook_id INT NOT NULL REFERENCES playbooks(id) ON DELETE CASCADE,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (incident_id, playbook_id)
-- Release 2.0: sign-in and access. People sign in with a password or single sign-on (OpenID Connect); a role's
-- permissions are the ticks of the matrix in role_permissions (rules in app/rbac.py). Sessions keep only a hash.
CREATE TABLE IF NOT EXISTS roles (
  id          TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  builtin     BOOLEAN NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS role_permissions (
  role_id     TEXT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission  TEXT NOT NULL,
  PRIMARY KEY (role_id, permission)
);
CREATE TABLE IF NOT EXISTS users (
  id             SERIAL PRIMARY KEY,
  email          TEXT NOT NULL UNIQUE,
  name           TEXT NOT NULL DEFAULT '',
  role_id        TEXT NOT NULL REFERENCES roles(id),
  password_hash  TEXT,                              -- NULL: single sign-on only
  sso_issuer     TEXT,
  sso_subject    TEXT,
  active         BOOLEAN NOT NULL DEFAULT true,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at  TIMESTAMPTZ,
  UNIQUE (sso_issuer, sso_subject)
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash  TEXT PRIMARY KEY,                     -- SHA-256 of the cookie; the token itself is never stored
  user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at  TIMESTAMPTZ NOT NULL,
  ip          TEXT,
  user_agent  TEXT,
  via         TEXT NOT NULL DEFAULT 'password' CHECK (via IN ('password', 'sso'))
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS sso_pending (
  state       TEXT PRIMARY KEY,
  nonce       TEXT NOT NULL,
  verifier    TEXT NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS access_log (
  id      SERIAL PRIMARY KEY,
  ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
  actor   TEXT,
  action  TEXT NOT NULL,
  detail  JSONB NOT NULL DEFAULT '{}'
);
