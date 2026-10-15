// "Add a host": the one-line install a user runs themselves, and the form for connecting a server from AIOps
// (AIOps signs in once, installs the agent and keeps the data channel open - the user runs nothing).

export function installCommand({ origin, name }) {
  return `curl -fsSL ${origin}/install/agent.sh | AIOPS_HOST_NAME=${name} sh`;
}

export function missing(f) {
  if (!f.address.trim()) return "Enter the server address";
  if (!f.user.trim()) return "Enter the user to sign in as";
  if (f.auth === "password" ? !f.password : !f.key) return f.auth === "password" ? "Enter the password" : "Choose the key file";
  return null;
}

export function connectBody(name, f) {
  const body = { name, address: f.address.trim(), port: Number(f.port) || 22, user: f.user.trim(), ebpf: Boolean(f.ebpf) };
  if (f.auth === "password") return { ...body, password: f.password };
  return { ...body, private_key: f.key, ...(f.passphrase ? { passphrase: f.passphrase } : {}) };
}
