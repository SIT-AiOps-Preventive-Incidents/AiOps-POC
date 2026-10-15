// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { TUNNEL_PORTS, installCommand, tunnelCommand } from "./connect.js";

const origin = "http://cp26pt1.sit.kmutt.ac.th:8080";

test("a machine that reaches AIOps gets the plain one-line install", () => {
  assert.equal(installCommand({ origin, name: "db-01" }),
    "curl -fsSL http://cp26pt1.sit.kmutt.ac.th:8080/install/agent.sh | AIOPS_HOST_NAME=db-01 sh");
});

test("a machine behind a tunnel installs from, and sends to, its own end of the tunnel", () => {
  assert.equal(installCommand({ origin, name: "esg360-prod", tunnel: true }),
    "curl -fsSL http://127.0.0.1:18080/install/agent.sh | AIOPS_HOST_NAME=esg360-prod " +
    "AIOPS_API=http://127.0.0.1:18080 AIOPS_OTLP=http://127.0.0.1:14318 sh");
});

test("the tunnel is opened from the AIOps server and only listens on the far machine's loopback", () => {
  const cmd = tunnelCommand({ login: "poc@34.2.129.3" });
  assert.match(cmd, /^ssh -N /);
  assert.ok(cmd.includes(`-R 127.0.0.1:${TUNNEL_PORTS.api}:localhost:8080`));
  assert.ok(cmd.includes(`-R 127.0.0.1:${TUNNEL_PORTS.otlp}:localhost:4318`));
  assert.ok(cmd.includes("-o ExitOnForwardFailure=yes"));
  assert.ok(cmd.endsWith(" poc@34.2.129.3"));
});

test("an empty login still shows where it goes", () => {
  assert.ok(tunnelCommand({ login: "" }).endsWith(" user@server"));
});
