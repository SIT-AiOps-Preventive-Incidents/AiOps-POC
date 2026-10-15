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

export function connectBody(f) {
  const body = { name: hostName(f.name, f.address), address: f.address.trim(), port: Number(f.port) || 22,
    user: f.user.trim(), ebpf: Boolean(f.ebpf) };
  if (f.auth === "password") return { ...body, password: f.password };
  return { ...body, private_key: f.key, ...(f.passphrase ? { passphrase: f.passphrase } : {}) };
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
