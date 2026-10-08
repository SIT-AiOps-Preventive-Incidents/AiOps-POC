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
  runbooks: { list: () => get("/runbooks"), setEnabled: (id, enabled) => patch(`/runbooks/${id}`, { enabled }) },
  skills: { list: () => get("/skills") },
  notifications: { list: () => get("/notifications"), test: () => post("/notifications/test") },
  settings: { get: () => get("/settings"), update: (body) => patch("/settings", body) },
  scenarios: { run: (id) => post(`/scenarios/${id}/runs`) },
};
