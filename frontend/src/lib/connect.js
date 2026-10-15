// "Add a host": connect a server from AIOps (sign in once on the web page, AIOps does the rest), or the
// one-line install a user runs themselves on a laptop.
import { slug } from "./format.js";

export function installCommand({ origin, name }) {
  return `curl -fsSL ${origin}/install/agent.sh | AIOPS_HOST_NAME=${name} sh`;
}

export function hostName(name, address) {
  return slug((name || "").trim()) || slug(address.trim().replace(/[.:]/g, "-"));
}

export function missing(f) {
  if (!f.address.trim()) return "Enter the server address";
  if (!f.user.trim()) return "Enter the user to sign in as";
  if (f.auth === "password" ? !f.password : !f.key) return f.auth === "password" ? "Enter the password" : "Choose the key file";
  return null;
}

function credential(f) {
  return f.auth === "password" ? { password: f.password }
    : { private_key: f.key, ...(f.passphrase ? { passphrase: f.passphrase } : {}) };
}

export function connectBody(f) {
  return { name: hostName(f.name, f.address), address: f.address.trim(), port: Number(f.port) || 22,
    user: f.user.trim(), ebpf: Boolean(f.ebpf), ...credential(f) };
}

// The connect page can be opened for one machine or many (from the Fleet's "Monitor selected"): the address query
// is one address or a comma-separated list. A target keeps its discovered hostname when the Fleet passed one.
export function parseTargets(addressQuery, nameQuery) {
  const names = String(nameQuery || "").split(",").map((s) => s.trim());
  return String(addressQuery || "").split(",").map((s) => s.trim()).filter(Boolean)
    .map((address, i) => (names[i] ? { address, name: slug(names[i].replace(/[.:]/g, "-")) || undefined } : { address }));
}

// Bulk connect: one shared sign-in, many machines. The credential is used once per host and never stored.
export function bulkBody(f, targets) {
  return { targets, port: Number(f.port) || 22, user: f.user.trim(), ebpf: Boolean(f.ebpf), ...credential(f) };
}

export function missingCred(f) {
  if (!f.user.trim()) return "Enter the user to sign in as";
  if (f.auth === "password" ? !f.password : !f.key) return f.auth === "password" ? "Enter the password" : "Choose the key file";
  return null;
}

// How full the progress ring is: finished steps, plus half of the one being worked on. Full only when done.
export function progress(job) {
  if (!job) return { value: 0, label: "", state: "idle" };
  if (job.state === "done") return { value: 1, label: "Connected", state: "done" };
  const n = job.steps.length;
  const done = job.steps.filter((s) => s.state === "done").length;
  const cur = job.steps.find((s) => s.state === "running" || s.state === "failed");
  const value = Math.min((done + (cur?.state === "running" ? 0.5 : 0)) / n, 0.99);
  return { value, label: cur ? cur.label : "", state: job.state };
}

// "Remove agent": the platform asks, the agent removes itself on its next report (about a minute), then the
// server disappears from AIOps. Same ring as connecting; failed when the agent has not answered in 2 minutes.
export const REMOVAL_STEPS = [["ask", "Ask the agent to remove itself"], ["agent", "Agent removes the collector, tracer and its key"],
  ["gone", "Removed from AIOps"]];
export function removal({ requestedAt, now = Date.now() / 1000, gone = false }) {
  if (!requestedAt) return null;
  const late = !gone && now - requestedAt > 120;
  const states = gone ? ["done", "done", "done"] : late ? ["done", "failed", "pending"] : ["done", "running", "pending"];
  return { state: gone ? "done" : late ? "failed" : "running",
    steps: REMOVAL_STEPS.map(([key, label], i) => ({ key, label, state: states[i] })) };
}
