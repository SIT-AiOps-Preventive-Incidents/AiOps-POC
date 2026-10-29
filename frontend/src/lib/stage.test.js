// Run with: npm test (node --test)
import assert from "node:assert/strict";
import { test } from "node:test";
import { SEVERITY, stageOf } from "./stage.js";

test("each status lands on one of five steps, with a short label and a tone", () => {
  assert.deepEqual(stageOf("open"), { step: 0, label: "Detected", tone: "info" });
  assert.deepEqual(stageOf("analyzing"), { step: 1, label: "AI on it", tone: "info" });
  assert.deepEqual(stageOf("awaiting_approval"), { step: 2, label: "Your call", tone: "action" });
  assert.deepEqual(stageOf("remediating"), { step: 3, label: "Fixing", tone: "info" });
  assert.deepEqual(stageOf("verifying"), { step: 3, label: "Checking", tone: "info" });
  assert.deepEqual(stageOf("resolved"), { step: 4, label: "Fixed", tone: "ok" });
});

test("ends that are not a fix stop the track where they happened", () => {
  assert.equal(stageOf("rejected").label, "Rejected");
  assert.equal(stageOf("rejected").tone, "neutral");
  assert.equal(stageOf("remediation_failed").tone, "bad");
  assert.equal(stageOf("closed").label, "Closed");
  assert.equal(stageOf("whatever").step, 0);
});

test("severity is a level 1-3 for the signal bars", () => {
  assert.equal(SEVERITY.critical.level, 3);
  assert.equal(SEVERITY.major.level, 2);
  assert.equal(SEVERITY.minor.level, 1);
});
