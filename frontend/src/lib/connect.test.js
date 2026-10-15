// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { connectBody, hostName, installCommand, missing, progress } from "./connect.js";

const form = (o = {}) => ({ name: "", address: " 34.2.129.3 ", port: "", user: "poc", auth: "password", password: "pw", key: "", passphrase: "", ebpf: true, ...o });
const steps = (...states) => states.map((state, i) => ({ key: `s${i}`, label: `Step ${i}`, state }));

test("a machine that runs the command itself gets the plain one-line install", () => {
  assert.equal(installCommand({ origin: "http://cp26pt1.sit.kmutt.ac.th:8080", name: "db-01" }),
    "curl -fsSL http://cp26pt1.sit.kmutt.ac.th:8080/install/agent.sh | AIOPS_HOST_NAME=db-01 sh");
});

test("the name is optional: it comes from the address when left empty", () => {
  assert.equal(hostName("", "34.2.129.3"), "34-2-129-3");
  assert.equal(hostName("", " ESG.prod.example.com "), "esg-prod-example-com");
  assert.equal(hostName("ESG 360 Prod", "34.2.129.3"), "esg-360-prod");
});

test("the form asks for what is missing, one thing at a time", () => {
  assert.equal(missing(form({ address: " " })), "Enter the server address");
  assert.equal(missing(form({ user: "" })), "Enter the user to sign in as");
  assert.equal(missing(form({ password: "" })), "Enter the password");
  assert.equal(missing(form({ auth: "key" })), "Choose the key file");
  assert.equal(missing(form()), null);
});

test("only the chosen way to sign in is sent", () => {
  const p = connectBody(form({ key: "left-over" }));
  assert.deepEqual(p, { name: "34-2-129-3", address: "34.2.129.3", port: 22, user: "poc", ebpf: true, password: "pw" });
  const k = connectBody(form({ name: "esg360-prod", auth: "key", key: "KEY", passphrase: "pp", port: "2222", ebpf: false }));
  assert.deepEqual(k, { name: "esg360-prod", address: "34.2.129.3", port: 2222, user: "poc", ebpf: false, private_key: "KEY", passphrase: "pp" });
});

test("the ring fills with finished steps and is only full when everything is done", () => {
  assert.equal(progress(null).value, 0);
  assert.equal(progress({ state: "running", steps: steps("pending", "pending", "pending", "pending") }).value, 0);
  const mid = progress({ state: "running", steps: steps("done", "running", "pending", "pending") });
  assert.equal(mid.value, 0.375);                       // 1 done + half of the running one, out of 4
  assert.equal(mid.label, "Step 1");
  assert.ok(progress({ state: "running", steps: steps("done", "done", "done", "running") }).value < 1);
  assert.deepEqual(progress({ state: "done", steps: steps("done", "done", "done", "done") }), { value: 1, label: "Connected", state: "done" });
  const bad = progress({ state: "failed", error: "nope", steps: steps("done", "failed", "pending", "pending") });
  assert.equal(bad.state, "failed");
  assert.equal(bad.value, 0.25);
});

test("removing an agent shows the same ring: asked, agent removes itself, gone", async () => {
  const { removal } = await import("./connect.js");
  assert.equal(removal({ requestedAt: null }), null);
  const asked = removal({ requestedAt: 1000, now: 1010, gone: false });
  assert.deepEqual(asked.steps.map((s) => s.state), ["done", "running", "pending"]);
  assert.equal(asked.state, "running");
  assert.equal(removal({ requestedAt: 1000, now: 1200, gone: false }).state, "failed");   // no answer in 2 minutes
  const done = removal({ requestedAt: 1000, now: 1050, gone: true });
  assert.equal(done.state, "done");
  assert.equal(progress(done).value, 1);
});
