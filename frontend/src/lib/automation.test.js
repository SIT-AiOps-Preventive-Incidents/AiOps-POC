// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { playbookBody, playbookForm, playbookSentence, runbookBody, runbookForm, skillBody, skillForm, toggle } from "./automation.js";

test("toggling a chip adds it once and removes it again", () => {
  assert.deepEqual(toggle(["a"], "b"), ["a", "b"]);
  assert.deepEqual(toggle(["a", "b"], "a"), ["b"]);
});

test("a skill form round-trips and trims what people type", () => {
  const f = skillForm({ id: "custom-pay", name: "Pay", description: "", kinds: ["error_rate"], tools: ["searchLogs"], instructions: "x", enabled: true });
  assert.deepEqual(skillBody({ ...f, name: "  Payments  " }),
    { name: "Payments", description: "", kinds: ["error_rate"], tools: ["searchLogs"], instructions: "x", enabled: true });
  assert.equal(skillForm().enabled, true);
});

test("runbook steps are one per line, blank lines dropped, and the service comes back for editing", () => {
  const b = runbookBody({ title: " Checkout 5xx ", kind: "error_rate", service: " checkout ", action_type: "rollback_deployment",
    root_cause: "bad release", stepsText: "Check deploy\n\n  Roll back  \n" });
  assert.deepEqual(b.steps, ["Check deploy", "Roll back"]);
  assert.equal(b.service, "checkout");
  const f = runbookForm({ title: "t", kind: "latency", action_params: { service: "api" }, action_type: "manual", root_cause: "", steps: ["a", "b"] });
  assert.equal(f.service, "api"); assert.equal(f.stepsText, "a\nb");
});

test("a playbook body leaves out what was not set, and escalation is a whole number of minutes", () => {
  const b = playbookBody({ name: "On-call", enabled: true, kinds: [], min_severity: "", entity: " ", owner_team: "team-pay", escalate: "30" });
  assert.deepEqual(b, { name: "On-call", enabled: true, trigger: {}, actions: { owner_team: "team-pay", escalate_after_min: 30 } });
  assert.equal(playbookBody({ ...playbookForm(), name: "x", escalate: "" }).actions.escalate_after_min, undefined);
  assert.equal(playbookForm({ name: "p", trigger: { kinds: ["latency"] }, actions: { escalate_after_min: 15 } }).escalate, "15");
});

test("a playbook reads as one sentence a manager can check", () => {
  const p = { trigger: { kinds: ["error_rate", "latency"], min_severity: "major", entity: "checkout*" },
    actions: { owner_team: "team-payments", escalate_after_min: 30 } };
  assert.equal(playbookSentence(p),
    "When failure rate or slow responses, major or worse, on checkout* → hand to team-payments · escalate after 30 min without approval");
  assert.equal(playbookSentence({ trigger: {}, actions: {} }), "When any incident → owner from the service");
});
