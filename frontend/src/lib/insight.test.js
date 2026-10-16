// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { approveLabel, confidenceLevel, consequence, evidenceSource, rollup, speedVitals } from "./insight.js";

test("confidence is shown as a level with what to do, not a bare percentage", () => {
  assert.equal(confidenceLevel(0.93).level, "high");
  assert.equal(confidenceLevel(0.8).level, "high");
  assert.equal(confidenceLevel(0.79).level, "medium");
  assert.equal(confidenceLevel(0.5).level, "medium");
  assert.equal(confidenceLevel(0.49).level, "low");
  assert.match(confidenceLevel(0.9).advice, /evidence/i);
  assert.match(confidenceLevel(0.2).advice, /lead/i);
});

test("missing confidence counts as low, never as high", () => {
  assert.equal(confidenceLevel(null).level, "low");
  assert.equal(confidenceLevel(undefined).level, "low");
});

test("a summary the model did not write is never shown as high", () => {
  assert.equal(confidenceLevel(0.95, { llmOk: false }).level, "medium");
});

test("each evidence line is tagged with the data it came from", () => {
  assert.equal(evidenceSource("distributed traces show the failing span originates in frontend"), "Traces");
  assert.equal(evidenceSource("Most frequent error log in frontend (105x): GET /api failed"), "Logs");
  assert.equal(evidenceSource("Current failure rate of frontend by running version: v1.2.0 17%."), "Metrics");
  assert.equal(evidenceSource("Host napat-mac: CPU None%, memory 78.2%, disk 94.62%"), "Metrics");
  assert.equal(evidenceSource("No deployment of frontend in the last 60 minutes"), "Deploys");
  assert.equal(evidenceSource("link core-1:eth2 is down, BGP peer lost"), "Network");
  assert.equal(evidenceSource("This machine is observe-only"), null);
});

test("the approval states what will run and who notices", () => {
  const dr = { ok: true, impact: "requests on frontend-b may fail (~5 s).", changes: ["docker restart frontend-b"] };
  const c = consequence({ type: "restart_instance", label: "Restart instance frontend-b of frontend", dry_run: dr });
  assert.deepEqual(c.runs, ["docker restart frontend-b"]);
  assert.equal(c.impact, "requests on frontend-b may fail (~5 s).");
  assert.equal(c.manual, false);
});

test("a manual step changes nothing", () => {
  const c = consequence({ type: "manual", label: "No automated action", dry_run: { ok: true, changes: [] } });
  assert.equal(c.manual, true);
  assert.deepEqual(c.runs, []);
  assert.equal(consequence(null), null);
});

test("the approve button names the action instead of saying yes", () => {
  assert.equal(approveLabel({ type: "restart_instance", label: "Restart instance frontend-b of frontend" }),
    "Approve: Restart instance frontend-b of frontend");
  assert.equal(approveLabel({ type: "manual", label: "x" }), "Acknowledge - I'll handle it");
  assert.equal(approveLabel(null), "Approve fix");
});

test("health rolls up as affected out of total", () => {
  const r = rollup([{ status: "healthy" }, { status: "problem" }, { status: "down" }, { status: "no-data" }]);
  assert.deepEqual(r, { affected: 2, total: 4, quiet: 1 });
  assert.deepEqual(rollup([]), { affected: 0, total: 0, quiet: 0 });
});

test("speed is split: the AI's own investigation time apart from the fix after approval", () => {
  const [inv, fix] = speedVitals({ investigate_s: 82, fix_s: 66, mttr_s: 52560 });
  assert.equal(inv.key, "investigate");
  assert.equal(inv.seconds, 82);
  assert.equal(fix.key, "fix");
  assert.equal(fix.seconds, 66);
});

test("speed never falls back to the end-to-end time, which is mostly waiting for a person", () => {
  const [inv, fix] = speedVitals({ mttr_s: 52560 });
  assert.equal(inv.seconds, null);
  assert.equal(fix.seconds, null);
  assert.deepEqual(speedVitals(undefined).map((v) => v.seconds), [null, null]);
});
