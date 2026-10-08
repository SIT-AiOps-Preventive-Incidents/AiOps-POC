export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };
export type HealthStatus =
  | "healthy"
  | "problem"
  | "no-data"
  | "offline"
  | "down"
  | string;
export type IncidentStatus =
  | "open"
  | "analyzing"
  | "awaiting_approval"
  | "remediating"
  | "verifying"
  | "resolved"
  | "rejected"
  | "closed"
  | "remediation_failed"
  | string;
export type SeriesPoint = [number, number | null];

export interface LlmStatus {
  up: boolean;
  active: string;
  models: string[];
  [key: string]: unknown;
}
export interface DetectorStatus {
  ts?: number;
  checks?: number;
  [key: string]: unknown;
}
export interface Kpi {
  open: number;
  total: number;
  mttd_s: number | null;
  mtta_s: number | null;
  mttr_s: number | null;
  avg_score: number | null;
  awaiting_approval: number;
}

export interface AppRecord {
  id: number;
  name: string;
  service_name: string;
  language?: string;
  team?: string;
  owner?: string;
  repo?: string;
  environment?: string;
  container?: string;
  admin_url?: string;
  kind?: string;
  created_at?: number;
  service?: string;
  rps?: number | null;
  error_rate?: number | null;
  p95_ms?: number | null;
  status?: HealthStatus;
  problem_id?: number | null;
  version?: string | null;
  commit?: string | null;
  deployed_at?: number | null;
}

export interface HostRecord {
  id: number;
  name: string;
  address: string;
  os?: string;
  environment?: string;
  labels?: Record<string, string>;
  owner?: string;
  agent?: string;
  kind?: string;
  created_at?: number;
  up?: number | null;
  cpu?: number | null;
  mem?: number | null;
  disk?: number | null;
  load?: number | null;
  status?: HealthStatus;
  problem_id?: number | null;
}

export interface DryRunCheck {
  name: string;
  ok: boolean;
  detail: string;
}
export interface DryRun {
  ok: boolean;
  checks?: DryRunCheck[];
  changes?: string[];
  impact?: string;
}
export interface ActionCandidate {
  label?: string;
  type?: string;
  params?: Record<string, JsonValue>;
  dry_run?: DryRun;
  [key: string]: unknown;
}
export interface IncidentStep {
  kind: string;
  title: string;
  detail?: string;
  ms?: number;
  meta?: { ms?: number };
  output?: Record<string, unknown>;
  checks?: DryRunCheck[];
  changes?: string[];
  impact?: string;
  facts?: Record<string, unknown>;
  candidates?: ActionCandidate[];
  rejected?: string;
}

export interface Incident {
  id: number;
  title: string;
  kind: string;
  entity_type: string;
  entity: string;
  severity: string;
  status: IncidentStatus;
  started_at?: number | null;
  detected_at: number;
  analyzed_at?: number | null;
  approved_at?: number | null;
  resolved_at?: number | null;
  signal?: Record<string, unknown>;
  skill?: string;
  skill_reason?: string;
  path?: string;
  root_cause?: string;
  summary?: string;
  confidence?: number | null;
  facts?: Record<string, unknown>;
  evidence?: string[];
  runbook?: string[];
  action?: ActionCandidate;
  candidates?: ActionCandidate[];
  steps?: IncidentStep[];
  execution?: Record<string, unknown>;
  runbook_id?: number | null;
  approver?: string;
  owner?: string;
  llm_model?: string;
  llm_ok?: number;
  analysis_ms?: number;
  score?: number | null;
  feedback?: string;
  rca_correct?: number | null;
  dry_run?: DryRun;
  notifications?: NotificationRecord[];
  grafana_url?: string;
}

export interface OverviewResponse {
  services: AppRecord[];
  hosts: HostRecord[];
  open_problems: Incident[];
  kpi: Kpi;
  detector: DetectorStatus;
  llm: LlmStatus;
  grafana_url: string;
}
export interface DiscoveryResponse {
  services: Array<{ service_name: string; rps: number | null }>;
  hosts: string[];
  otlp_endpoint: string;
  api: string;
}
export interface VerifyResponse {
  metrics: boolean;
  logs: boolean;
  traces: boolean;
  rps?: number | null;
  log_lines_5m?: number;
}

export interface Deployment {
  id: number;
  service: string;
  version: string;
  commit_hash: string;
  author: string;
  message: string;
  profile?: string;
  ts: number;
}
export interface LogEntry {
  ts: number;
  level?: string;
  line: string;
  [key: string]: unknown;
}
export interface TraceSummary {
  traceID: string;
  rootTraceName: string;
  rootServiceName: string;
  startTimeUnixNano: number;
  durationMs?: number;
}
export interface TraceSpan {
  id: string;
  parent?: string;
  service: string;
  instance?: string;
  name: string;
  start: number;
  end: number;
  error?: boolean;
  status_msg?: string;
}
export interface ServiceDetailResponse {
  app: AppRecord;
  health: AppRecord;
  series: Record<"rps" | "error_rate" | "p95", SeriesPoint[]>;
  endpoints: Array<{ name: string; rps: number; error_rate: number }>;
  versions: Array<{
    version: string;
    commit: string;
    rps?: number;
    error_rate: number;
  }>;
  deployments: Deployment[];
  logs: LogEntry[];
  traces: TraceSummary[];
  outbound_rps?: string | null;
  incidents: Incident[];
}

export interface ProcessInfo {
  name: string;
  pid: number;
  cpu: number;
  mem: number;
}
export interface ContainerInfo {
  name: string;
  image: string;
  cpu_pct: number;
  mem_mb: number;
  status?: string;
}
export interface HostDetailResponse {
  host: HostRecord;
  series: Record<"cpu" | "mem" | "disk" | "load", SeriesPoint[]>;
  processes: ProcessInfo[];
  containers: ContainerInfo[];
  incidents: Incident[];
}

export interface MapInstance {
  id: string;
  rps?: number | null;
  error_rate?: number | null;
  problem_id?: number | null;
}
export interface MapNode {
  id: string;
  kind?: string;
  owner?: string;
  language?: string;
  rps?: number | null;
  error_rate?: number | null;
  p95_ms?: number | null;
  problem_id?: number | null;
  instances?: MapInstance[];
}
export interface MapEdge {
  from: string;
  to: string;
  rps?: number | null;
  error_rate?: number | null;
}
export interface ServiceMapResponse {
  nodes: MapNode[];
  edges: MapEdge[];
  entry: string[];
  hosts: HostRecord[];
  traces_sampled: number;
}

export interface SkillRecord {
  id: string;
  name: string;
  category: string;
  description: string;
  tools: string[];
  runs: number;
  avg_score: number | null;
  accuracy: number | null;
  avg_analysis_s: number | null;
  lessons: string[];
}
export interface RunbookRecord {
  id: number;
  title: string;
  kind: string;
  skill: string;
  root_cause: string;
  runbook: string[];
  action: ActionCandidate;
  uses: number;
  score_sum: number;
  score_n: number;
  enabled: number;
  source_incident: number;
  created_at: number;
  updated_at: number;
  signature: string;
}
export interface NotificationRecord {
  id: number;
  ts: number;
  channel?: string;
  incident_id?: number;
  event: string;
  status: string;
}
export interface SettingsResponse {
  settings: Record<string, string>;
  llm: LlmStatus;
  public_url: string;
  grafana_url: string;
}
