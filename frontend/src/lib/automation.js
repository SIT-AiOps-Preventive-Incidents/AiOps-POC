// Forms for what a team writes itself: skills, skill sets, runbooks and playbooks. The server checks the same rules
// (app/automation.py); these only shape what people type into the body the API takes, and read it back for editing.

export const KIND_LABEL = {
  error_rate: "failure rate", latency: "slow responses", traffic_drop: "traffic drop", host_cpu: "host CPU",
  host_mem: "host memory", host_disk: "host disk", host_down: "host down", auth_bruteforce: "login attacks",
  log_errors: "error logs", container_cpu: "container CPU", container_mem: "container memory", container_down: "container down",
};
export const FIX_LABEL = {
  rollback_deployment: "Roll back the release", restart_service: "Restart the service", restart_instance: "Restart one instance",
  block_ip: "Block the source IP", manual: "Hand to a person",
};
export const kindLabel = (k) => KIND_LABEL[k] || k;

export const toggle = (arr, v) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

export const skillForm = (s = {}) => ({ name: s.name || "", description: s.description || "", kinds: [...(s.kinds || [])],
  tools: [...(s.tools || [])], instructions: s.instructions || "", enabled: s.enabled ?? true });
export const skillBody = (f) => ({ name: f.name.trim(), description: f.description.trim(), kinds: f.kinds, tools: f.tools,
  instructions: f.instructions.trim(), enabled: f.enabled });

export const runbookForm = (r = {}) => ({ title: r.title || "", kind: r.kind || "error_rate", service: r.action_params?.service || "",
  action_type: r.action_type || "manual", root_cause: r.root_cause || "", stepsText: (r.steps || []).join("\n") });
export const runbookBody = (f) => ({ title: f.title.trim(), kind: f.kind, service: f.service.trim(), action_type: f.action_type,
  root_cause: f.root_cause.trim(), steps: f.stepsText.split("\n").map((s) => s.trim()).filter(Boolean) });

export const playbookForm = (p = {}) => ({ name: p.name || "", enabled: p.enabled ?? true, kinds: [...(p.trigger?.kinds || [])],
  min_severity: p.trigger?.min_severity || "", entity: p.trigger?.entity || "", owner_team: p.actions?.owner_team || "",
  escalate: p.actions?.escalate_after_min ? String(p.actions.escalate_after_min) : "" });
export function playbookBody(f) {
  const trigger = {}, actions = {};
  if (f.kinds.length) trigger.kinds = f.kinds;
  if (f.min_severity) trigger.min_severity = f.min_severity;
  if (f.entity.trim()) trigger.entity = f.entity.trim();
  if (f.owner_team.trim()) actions.owner_team = f.owner_team.trim();
  if (String(f.escalate).trim()) actions.escalate_after_min = Math.round(Number(f.escalate));
  return { name: f.name.trim(), enabled: f.enabled, trigger, actions };
}

export function playbookSentence(p) {
  const t = p.trigger || {}, a = p.actions || {};
  const when = [t.kinds?.length ? t.kinds.map(kindLabel).join(" or ") : "any incident"];
  if (t.min_severity) when.push(t.min_severity === "critical" ? "critical only" : `${t.min_severity} or worse`);
  if (t.entity) when.push(`on ${t.entity}`);
  const then = [a.owner_team ? `hand to ${a.owner_team}` : "owner from the service"];
  if (a.escalate_after_min) then.push(`escalate after ${a.escalate_after_min} min without approval`);
  return `When ${when.join(", ")} → ${then.join(" · ")}`;
}
