import { rollup } from "./insight.js";
import { SEVERITY } from "./stage.js";

export function overviewSnapshot({ services = [], hosts = [], open_problems: incidents = [], kpi = {}, detector, llm }, now) {
  const count = (...statuses) => incidents.filter((i) => statuses.includes(i.status)).length;
  const health = (items) => {
    const { total, affected } = rollup(items);
    const healthy = items.filter((i) => i.status === "healthy").length;
    return { total, healthy, affected, quiet: total - healthy - affected };
  };
  return {
    services: health(services), hosts: health(hosts),
    open: kpi.open ?? incidents.length,
    awaiting: kpi.awaiting_approval ?? count("awaiting_approval"),
    analyzing: kpi.analyzing ?? count("analyzing"),
    fixing: kpi.fixing ?? count("remediating", "verifying"),
    failed: kpi.fix_failed ?? count("remediation_failed"),
    detectionLive: !!detector?.ts && !detector.error && now - detector.ts < 60,
    aiReady: llm?.up === true && !!llm.active && llm.models?.includes(llm.active),
  };
}

export function dashboardTone(snapshot, stale) {
  if (stale) return "stale";
  const { open, awaiting, failed, services, hosts, detectionLive } = snapshot;
  if (awaiting || failed || services.affected || hosts.affected) return "attention";
  if (open) return "active";
  if (!detectionLive || !services.total && !hosts.total || services.quiet || hosts.quiet) return "limited";
  return "healthy";
}

export function priorityIncidents(incidents) {
  const priority = (i) => ["awaiting_approval", "remediation_failed"].includes(i.status) ? 1 : 0;
  const severity = (i) => SEVERITY[i.severity]?.level ?? 0;
  return [...incidents].sort((a, b) => priority(b) - priority(a) || severity(b) - severity(a) || b.detected_at - a.detected_at);
}

export function overviewFacts(snapshot, stale) {
  if (!snapshot) return {};
  return {
    open_incidents: snapshot.open, awaiting_approval: snapshot.awaiting, ai_investigations: snapshot.analyzing,
    fixes_in_progress: snapshot.fixing, failed_fixes: snapshot.failed,
    monitored_services: snapshot.services.total, services_with_issues: snapshot.services.affected,
    monitored_hosts: snapshot.hosts.total, hosts_with_issues: snapshot.hosts.affected,
    resources_without_data: snapshot.services.quiet + snapshot.hosts.quiet,
    [`detector_${snapshot.detectionLive ? "active" : "unconfirmed"}`]: 1,
    ...(stale ? { stale_data: 1 } : {}),
  };
}
