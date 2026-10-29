// Run with: npm test (node --test)
import assert from "node:assert/strict";
import { test } from "node:test";
import { bodyFor, fieldsFor, missing, verdictTone } from "./cloudform.js";

const PVE = { id: "proxmox", label: "Proxmox VE", config: ["url"], optional: ["pool", "verify_tls"], secret: ["token_id", "token_secret"] };

test("a provider spec becomes labelled fields, secrets hidden, optional ones marked", () => {
  const f = fieldsFor(PVE);
  assert.deepEqual(f.map((x) => x.key), ["url", "pool", "verify_tls", "token_id", "token_secret"]);
  assert.equal(f.find((x) => x.key === "token_secret").type, "password");
  assert.equal(f.find((x) => x.key === "url").required, true);
  assert.equal(f.find((x) => x.key === "pool").required, false);
  assert.equal(f.find((x) => x.key === "verify_tls").type, "switch");
  assert.match(f.find((x) => x.key === "url").placeholder, /^https:\/\//);
});

test("the body splits what is safe to keep (config) from the credential (secret), and drops blanks", () => {
  const b = bodyFor(PVE, " GIST ", { url: "https://pve.gist:8006", pool: "", verify_tls: false, token_id: "a@pve!x", token_secret: "s" });
  assert.deepEqual(b, { provider: "proxmox", name: "GIST", config: { url: "https://pve.gist:8006", verify_tls: false },
    secret: { token_id: "a@pve!x", token_secret: "s" } });
});

test("missing lists every required field still empty", () => {
  assert.deepEqual(missing(PVE, "", { url: "https://x" }), ["name", "token_id", "token_secret"]);
  assert.deepEqual(missing(PVE, "n", { url: "u", token_id: "i", token_secret: "s" }), []);
});

test("verdicts map to a tone the eye reads before the words", () => {
  assert.equal(verdictTone("agent_silent"), "bad");
  assert.equal(verdictTone("stopped_in_cloud"), "warn");
  assert.equal(verdictTone("ok"), "ok");
  assert.equal(verdictTone("not_monitored"), "neutral");
});
