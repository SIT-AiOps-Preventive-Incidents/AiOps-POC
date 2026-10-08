// Domain vocabulary: how backend states map to words, tones and icons. One place to change wording.

export const INCIDENT_STATUS = {
  open: { label: "New", tone: "warn" },
  analyzing: { label: "AI investigating", tone: "ai" },
  awaiting_approval: { label: "Needs approval", tone: "ai" },
  remediating: { label: "Applying fix", tone: "info" },
  verifying: { label: "Checking fix", tone: "info" },
  resolved: { label: "Resolved", tone: "ok" },
  rejected: { label: "Rejected", tone: "neutral" },
  closed: { label: "Closed", tone: "neutral" },
  remediation_failed: { label: "Fix didn't work", tone: "bad" },
};
export const ACTIVE = ["open", "analyzing", "remediating", "verifying", "remediation_failed"];
export const CLOSED = ["resolved", "rejected", "closed"];

export const INCIDENT_KIND = {
  error_rate: { icon: "warning", color: "var(--c-bad)", label: "Failure rate increase" },
  latency: { icon: "clock", color: "var(--c-warn)", label: "Slow responses" },
  host_cpu: { icon: "developer_board", color: "var(--c-chart-4)", label: "CPU saturation" },
  host_mem: { icon: "developer_board", color: "var(--c-chart-4)", label: "Memory saturation" },
  host_disk: { icon: "hard_drive", color: "var(--c-chart-4)", label: "Low disk space" },
  host_down: { icon: "server", color: "var(--c-bad)", label: "Host unavailable" },
  auth_bruteforce: { icon: "shield", color: "var(--c-chart-5)", label: "Password attack" },
};

export const STEP_KIND = {
  tool: { icon: "search", color: "var(--c-primary)" },
  llm: { icon: "sparkle", color: "var(--c-ai)" },
  skill: { icon: "wand", color: "var(--c-warn)" },
  analysis: { icon: "list", color: "var(--c-chart-5)" },
  memory: { icon: "book", color: "var(--c-chart-5)" },
  dryrun: { icon: "wrench", color: "var(--c-chart-5)" },
  guard: { icon: "shield", color: "var(--c-ok)" },
  done: { icon: "checkmark", color: "var(--c-ok)" },
  info: { icon: "sparkle", color: "var(--c-text-3)" },
};

// Health of a service/host -> dot tone
export const HEALTH_TONE = { healthy: "ok", problem: "bad", down: "bad", offline: "neutral", "no-data": "neutral" };

const LANGS = [
  [/python|uvicorn|gunicorn/, "python"], [/node|javascript|typescript|bun|deno/, "node"], [/java/, "java"],
  [/\.?net|c#|csharp|dotnet/, "dotnet"], [/nginx/, "nginx"], [/docker/, "docker"], [/postgres/, "postgres"],
];
const KNOWN_LOGOS = new Set(["python", "node", "java", "dotnet", "nginx", "docker", "apple", "linux", "grafana",
  "prometheus", "otel", "teams", "ollama"]);

export function languageLogo(lang) {
  const l = (lang || "").toLowerCase();
  const hit = LANGS.find(([re]) => re.test(l));
  return hit && KNOWN_LOGOS.has(hit[1]) ? hit[1] : null;
}
export function osLogo(os) {
  if (/darwin|mac/i.test(os || "")) return "apple";
  if (/linux|ubuntu|debian|centos|rhel/i.test(os || "")) return "linux";
  return null;
}
export const kindIcon = (kind) => ({ network: "shield", process: "apps", external: "database", client: "globe" }[kind] || "cube");
