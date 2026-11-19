// Where an incident is on its way to a fix: five steps, so a list shows progress at a glance instead of a pill.
// 0 Detected  1 AI investigating  2 your call (approve)  3 fixing / checking  4 fixed
const STAGE = {
  open: [0, "Detected", "info"], analyzing: [1, "AI on it", "info"], awaiting_approval: [2, "Your call", "action"],
  remediating: [3, "Fixing", "info"], verifying: [3, "Checking", "info"], resolved: [4, "Fixed", "ok"],
  rejected: [2, "Rejected", "neutral"], closed: [1, "Closed", "neutral"], remediation_failed: [3, "Fix failed", "bad"],
};
export const STEPS = 5;
export function stageOf(status) {
  const [step, label, tone] = STAGE[status] || [0, status || "Unknown", "neutral"];
  return { step, label, tone };
}
// severity as a 1-3 signal: how loud, not a coloured badge
export const SEVERITY = { critical: { level: 3, label: "Critical" }, major: { level: 2, label: "Major" }, minor: { level: 1, label: "Minor" } };
