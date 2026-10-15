// Commands shown on "Add a host". A machine outside the campus network cannot reach AIOps, so AIOps opens an SSH
// tunnel to it instead: the far machine then talks to AIOps through its own loopback (nothing is opened on it).

export const TUNNEL_PORTS = { api: 18080, otlp: 14318 };
const LOCAL_API = `http://127.0.0.1:${TUNNEL_PORTS.api}`;
const LOCAL_OTLP = `http://127.0.0.1:${TUNNEL_PORTS.otlp}`;

export function installCommand({ origin, name, tunnel = false }) {
  if (!tunnel) return `curl -fsSL ${origin}/install/agent.sh | AIOPS_HOST_NAME=${name} sh`;
  return `curl -fsSL ${LOCAL_API}/install/agent.sh | AIOPS_HOST_NAME=${name} AIOPS_API=${LOCAL_API} AIOPS_OTLP=${LOCAL_OTLP} sh`;
}

export function tunnelCommand({ login }) {
  return ["ssh -N", "-o ServerAliveInterval=30", "-o ExitOnForwardFailure=yes",
    `-R 127.0.0.1:${TUNNEL_PORTS.api}:localhost:8080`, `-R 127.0.0.1:${TUNNEL_PORTS.otlp}:localhost:4318`,
    login || "user@server"].join(" ");
}
