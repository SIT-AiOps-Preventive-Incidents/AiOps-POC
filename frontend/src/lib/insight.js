// How AI findings are presented so a person can trust or doubt them quickly. Pure: no Vue, unit-tested.

// Confidence as a level that says what to do (PAIR / incident.io pattern), not a bare percentage.
const LEVELS = {
  high: { label: "High confidence", advice: "The evidence agrees. Review the fix and approve if it looks right." },
  medium: { label: "Medium confidence", advice: "Read the evidence before approving; part of the cause is not confirmed." },
  low: { label: "Low confidence", advice: "Treat this as a lead, not an answer. Check the evidence yourself." },
};
export function confidenceLevel(c, { llmOk = true } = {}) {
  let level = c == null ? "low" : c >= 0.8 ? "high" : c >= 0.5 ? "medium" : "low";
  if (level === "high" && llmOk === false) level = "medium";
  return { level, ...LEVELS[level] };
}

// Which data an evidence line came from, so each claim is tied to a source.
const SOURCES = [
  ["Traces", /\btraces?\b|\bspans?\b/i],
  ["Logs", /\blogs?\b|exception|traceback/i],
  ["Deploys", /\bdeploy(ment|ed)?s?\b|\brollback\b/i],
  ["Network", /\blink\b|\binterface\b|\bbgp\b|\bswitch\b|\brouter\b/i],
  ["Metrics", /%|\brate\b|\blatency\b|\bp95\b|\bcpu\b|\bmemory\b|\bdisk\b|req\/s/i],
];
export function evidenceSource(text) {
  const hit = SOURCES.find(([, re]) => re.test(text || ""));
  return hit ? hit[0] : null;
}

// What approving will actually do, in the words of the dry run.
export function consequence(action) {
  if (!action) return null;
  const dr = action.dry_run || {};
  return { manual: action.type === "manual", runs: dr.changes || [], impact: dr.impact || "" };
}
export function approveLabel(action) {
  if (!action) return "Approve fix";
  return action.type === "manual" ? "Acknowledge - I'll handle it" : `Approve: ${action.label}`;
}

// "2 of 12 affected" roll-up; no-data is counted separately so silence is not hidden as health.
export function rollup(items) {
  const affected = items.filter((s) => ["problem", "down"].includes(s.status)).length;
  const quiet = items.filter((s) => ["no-data", "offline"].includes(s.status)).length;
  return { affected, total: items.length, quiet };
}
