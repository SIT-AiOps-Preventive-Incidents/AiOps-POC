// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { connectBody, installCommand, missing } from "./connect.js";

const form = (o = {}) => ({ address: " 34.2.129.3 ", port: "", user: "poc", auth: "key", password: "", key: "KEY", passphrase: "", ebpf: true, ...o });

test("a machine that runs the command itself gets the plain one-line install", () => {
  assert.equal(installCommand({ origin: "http://cp26pt1.sit.kmutt.ac.th:8080", name: "db-01" }),
    "curl -fsSL http://cp26pt1.sit.kmutt.ac.th:8080/install/agent.sh | AIOPS_HOST_NAME=db-01 sh");
});

test("the form asks for what is missing, one thing at a time", () => {
  assert.equal(missing(form({ address: " " })), "Enter the server address");
  assert.equal(missing(form({ user: "" })), "Enter the user to sign in as");
  assert.equal(missing(form({ key: "" })), "Choose the key file");
  assert.equal(missing(form({ auth: "password" })), "Enter the password");
  assert.equal(missing(form()), null);
});

test("only the chosen way to sign in is sent", () => {
  const k = connectBody("esg360-prod", form({ password: "left-over" }));
  assert.deepEqual(k, { name: "esg360-prod", address: "34.2.129.3", port: 22, user: "poc", ebpf: true, private_key: "KEY" });
  const p = connectBody("esg360-prod", form({ auth: "password", password: "pw", port: "2222", ebpf: false }));
  assert.deepEqual(p, { name: "esg360-prod", address: "34.2.129.3", port: 2222, user: "poc", ebpf: false, password: "pw" });
  assert.equal(connectBody("x", form({ passphrase: "pp" })).passphrase, "pp");
});
