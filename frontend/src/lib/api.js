// REST client for /api/v1. Every call returns parsed JSON or throws ApiError with the server's error body.

export class ApiError extends Error {
  constructor(status, code, message, details) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details || {};
  }
}

async function request(method, path, body) {
  const res = await fetch(`/api/v1${path}`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && !path.startsWith("/auth/")) window.dispatchEvent(new CustomEvent("radarops:signed-out"));
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const e = data.error || {};
    throw new ApiError(res.status, e.code || "error", e.message || res.statusText, e.details);
  }
  return data;
}

const get = (p) => request("GET", p);
const post = (p, b = {}) => request("POST", p, b);
const put = (p, b = {}) => request("PUT", p, b);
const patch = (p, b) => request("PATCH", p, b);
const del = (p) => request("DELETE", p);
const enc = encodeURIComponent;

export const api = {
  overview: () => get("/overview"),
  insights: () => get("/insights"),
  health: () => get("/health"),

  services: {
    list: (kind) => get(`/services${kind ? `?kind=${kind}` : ""}`),
    get: (name) => get(`/services/${enc(name)}`),
    create: (body) => post("/services", body),
    update: (name, body) => patch(`/services/${enc(name)}`, body),
    remove: (name) => del(`/services/${enc(name)}`),
    discovered: () => get("/services/discovered"),
    telemetry: (name) => get(`/services/${enc(name)}/telemetry`),
  },

  hosts: {
    list: () => get("/hosts"),
    get: (name) => get(`/hosts/${enc(name)}`),
    create: (body) => post("/hosts", body),
    remove: (name) => del(`/hosts/${enc(name)}`),
    uninstall: (name) => post(`/hosts/${enc(name)}/uninstall`),
    netscan: (name) => post(`/hosts/${enc(name)}/netscan`),
  },

  map: {
    get: (refresh = false) => get(`/service-map${refresh ? "?refresh=true" : ""}`),
    startTest: (entry) => post("/test-requests", entry ? { entry } : {}),
    getTest: (id) => get(`/test-requests/${id}`),
    trace: (id) => get(`/traces/${id}`),
  },

  incidents: {
    list: (status) => get(`/incidents${status ? `?status=${status}` : ""}`),
    get: (id) => get(`/incidents/${id}`),
    close: (id) => patch(`/incidents/${id}`, { status: "closed" }),
    reanalyze: (id) => post(`/incidents/${id}/analyses`),
    decide: (id, body) => post(`/incidents/${id}/approvals`, body),
    feedback: (id, body) => put(`/incidents/${id}/feedback`, body),
  },

  deployments: { list: () => get("/deployments") },
  runbooks: { list: () => get("/runbooks"), setEnabled: (id, enabled) => patch(`/runbooks/${id}`, { enabled }),
    create: (body) => post("/runbooks", body), update: (id, body) => put(`/runbooks/${id}`, body), remove: (id) => del(`/runbooks/${id}`) },
  skills: { list: () => get("/skills"), create: (body) => post("/skills", body), update: (id, body) => patch(`/skills/${enc(id)}`, body),
    remove: (id) => del(`/skills/${enc(id)}`) },
  skillSets: { list: () => get("/skill-sets"), create: (body) => post("/skill-sets", body), update: (id, body) => patch(`/skill-sets/${id}`, body),
    remove: (id) => del(`/skill-sets/${id}`) },
  playbooks: { list: () => get("/playbooks"), create: (body) => post("/playbooks", body), update: (id, body) => patch(`/playbooks/${id}`, body),
    remove: (id) => del(`/playbooks/${id}`) },
  automation: { catalog: () => get("/automation/catalog") },
  teams: () => get("/teams"),
  notifications: { list: () => get("/notifications"), test: () => post("/notifications/test") },
  settings: { get: () => get("/settings"), update: (body) => patch("/settings", body) },
  connect: { ssh: (body) => post("/connect/ssh", body), bulk: (body) => post("/connect/ssh/bulk", body),
    job: (id) => get(`/connect/ssh/jobs/${id}`), links: () => get("/connect/ssh/links") },
  checks: { create: (body) => post("/checks", body), recent: (name) => get(`/checks/${enc(name)}`) },
  scenarios: { list: () => get("/scenarios"), run: (id) => post(`/scenarios/${id}/runs`) },
  cloud: {
    providers: () => get("/cloud/providers"),
    accounts: () => get("/cloud/accounts"),
    add: (body) => post("/cloud/accounts", body),
    sync: (id) => post(`/cloud/accounts/${id}/sync`),
    remove: (id) => del(`/cloud/accounts/${id}`),
    instances: (accountId) => get(`/cloud/instances${accountId ? `?account_id=${accountId}` : ""}`),
    events: () => get("/cloud/events"),
  },
  network: {
    get: () => get("/network"),
    scan: () => post("/network/scans"),
    events: () => get("/network/events"),
    graph: () => get("/network/graph"),
    recommendations: () => get("/network/recommendations"),
    discovered: (view) => get(`/network/discovered${view ? `?view=${view}` : ""}`),
  },
  auth: {
    providers: () => get("/auth/providers"),
    login: (body) => post("/auth/login", body),
    logout: () => post("/auth/logout"),
    me: () => get("/auth/me"),
    updateMe: (body) => patch("/auth/me", body),
    log: () => get("/auth/log"),
    sso: { get: () => get("/auth/sso"), update: (body) => patch("/auth/sso", body), test: (body) => post("/auth/sso/test", body) },
  },
  users: { list: () => get("/users"), create: (body) => post("/users", body), update: (id, body) => patch(`/users/${id}`, body),
    remove: (id) => del(`/users/${id}`) },
  roles: { get: () => get("/roles"), saveMatrix: (matrix) => put("/roles/matrix", { matrix }), create: (body) => post("/roles", body),
    rename: (id, label) => patch(`/roles/${enc(id)}`, { label }), remove: (id) => del(`/roles/${enc(id)}`) },
};
