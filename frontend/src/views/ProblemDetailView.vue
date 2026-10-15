<script setup>
import { computed } from "vue";
import FeedbackCard from "@/components/domain/FeedbackCard.vue";
import FixPanel from "@/components/domain/FixPanel.vue";
import InvestigationTimeline from "@/components/domain/InvestigationTimeline.vue";
import SeverityPill from "@/components/domain/SeverityPill.vue";
import StatusPill from "@/components/domain/StatusPill.vue";
import TraceWaterfall from "@/components/domain/TraceWaterfall.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { clock, clockSec, dur } from "@/lib/format";
import { confidenceLevel, evidenceSource } from "@/lib/insight";
import { useIncidentStore } from "@/stores/incidents";
import { useUiStore } from "@/stores/ui";
import { ref } from "vue";

const props = defineProps({ id: String });
const store = useIncidentStore();
const ui = useUiStore();
const inc = computed(() => store.byId[props.id]);
// blast radius: the other machines RadarOps monitors on the same network as the affected host - the first to check,
// and the same set the AI widens its search to.
const neighbours = ref([]);
let fetchedFor = "";
usePolling(async () => {
  await store.load(props.id);
  const i = inc.value;
  if (i && i.entity_type === "host" && i.entity !== fetchedFor) {
    fetchedFor = i.entity;
    try { neighbours.value = (await api.hosts.get(i.entity)).neighbours || []; } catch { neighbours.value = []; }
  }
}, 4000);

const steps = computed(() => {
  const i = inc.value;
  if (!i) return [];
  const ex = i.approval?.execution;
  const s = [
    { label: "Detected", ts: i.detected_at, done: true,
      hint: "The detector saw this entity leave its own learned-normal range and opened the incident." },
    { label: "AI investigated", ts: i.analyzed_at, done: !!i.analyzed_at,
      hint: i.analyzed_at ? `The AI read metrics, traces and logs and wrote the root cause${i.analysis_ms ? ` (took ${dur(i.analysis_ms / 1000)})` : ""}.` : "The AI is reading metrics, traces and logs." },
    { label: i.approval?.decision === "approved" ? `Approved by ${i.approval.approver}` : "Your approval",
      ts: i.approval?.decision === "approved" ? i.approval.decided_at : null, done: i.approval?.decision === "approved", you: true,
      hint: i.approval?.decision === "approved" ? `${i.approval.approver} approved the fix.` : "Nothing changes until a person approves the fix. The AI has already tested it in a dry run." },
    { label: "Fix applied", ts: ex?.ok ? ex.executed_at : null, done: !!ex?.ok,
      hint: ex?.ok ? "The approved fix ran on the affected service." : "The approved fix runs here, then RadarOps checks it worked." },
    { label: "Verified", ts: i.status === "resolved" ? i.resolved_at : null, done: i.status === "resolved",
      hint: "RadarOps re-checks the signal that tripped and resolves the incident only once it is back to normal." },
  ];
  const now = s.findIndex((x) => !x.done);
  const failed = ["remediation_failed", "rejected"].includes(i.status);
  return s.map((x, k) => ({ label: x.label, time: clock(x.ts), hint: x.hint, state: x.done ? "done" : k === now ? (failed ? "failed" : x.you ? "you" : "current") : "todo" }));
});
// what tripped the detector, said against this entity's own normal range
const METRIC = { error_rate: "Error rate", latency: "Response time (p95)", traffic_drop: "Traffic", host_cpu: "CPU", host_mem: "Memory",
  host_disk: "Disk", auth_bruteforce: "Failed logins", host_down: "Heartbeat" };
const fmtUnit = (v, u) => (v == null ? "-" : u === "ratio" ? `${(v * 100).toFixed(1)}%` : u === "%" ? `${Math.round(v)}%`
  : u === "ms" ? `${Math.round(v)} ms` : u === "req/s" ? `${Number(v).toFixed(2)} req/s` : `${v} ${u || ""}`.trim());
const trigger = computed(() => {
  const s = inc.value?.signal;
  if (!s || s.value == null) return null;
  const name = METRIC[s.kind] || s.kind;
  const now = fmtUnit(s.value, s.unit);
  if (s.normal_low != null) {
    const where = s.learned_from === "same_hour" ? `at this time of day over the last ${s.learned_days} days` : "over the last 24 hours";
    const lo = fmtUnit(s.normal_low, s.unit), hi = fmtUnit(s.normal_high, s.unit);
    return `${name} was ${now}. Normal for ${inc.value.entity} ${where} is ${lo === hi ? `about ${lo}` : `${lo} to ${hi}`}.`;
  }
  if (s.reason === "safety") return `${name} was ${now}, over the safety limit of ${fmtUnit(s.threshold, s.unit)}.`;
  return s.threshold ? `${name} was ${now}; the limit is ${fmtUnit(s.threshold, s.unit)}.` : `${name} was ${now}.`;
});
const conf = computed(() => confidenceLevel(inc.value?.confidence, { llmOk: inc.value?.llm_ok }));
const impact = computed(() => {
  const i = inc.value;
  const who = `${i.entity_type === "host" ? "Host" : "Service"} ${i.entity}`;
  return i.affected?.length ? `${who}, and ${i.affected.length} more: ${i.affected.join(", ")}` : `${who} only; nothing else is affected so far`;
});
const evidence = computed(() => (inc.value?.evidence || []).map((text) => ({ text, source: evidenceSource(text) })));
const samples = computed(() => (inc.value?.steps || []).filter((s) => s.kind === "tool" && s.data?.output?.samples?.length)
  .flatMap((s) => s.data.output.samples).slice(0, 4));
const trace = ref(null);
const traceOpen = ref(false);
async function openTrace(id) {
  try { trace.value = await api.map.trace(id); traceOpen.value = true; } catch (e) { ui.toast(e.message); }
}
</script>
<template>
  <div v-if="inc" class="page">
    <UiPageHeader :title="inc.title" :back="{ to: '/problems', label: 'Incidents' }">
      <template #subtitle><span class="facts"><span>{{ inc.entity_type === "host" ? "Host" : "Service" }} <b>{{ inc.entity }}</b></span>
        <span v-if="inc.affected.length">Also affected <b>{{ inc.affected.join(", ") }}</b></span><span>Detected <b>{{ clockSec(inc.detected_at) }}</b></span>
        <span>Owner <b>{{ inc.owner || "unassigned" }}</b></span><span class="mono dim">P-{{ inc.id }}</span></span></template>
      <SeverityPill :severity="inc.severity" /><StatusPill :status="inc.status" />
    </UiPageHeader>
    <UiStepper :steps="steps" />
    <div class="split mt">
      <div class="stack">
        <UiCard title="What happened" icon="search">
          <template v-if="inc.root_cause">
            <dl class="rca">
              <dt>Root cause</dt><dd class="rc">{{ inc.root_cause }}</dd>
              <template v-if="trigger"><dt>What failed</dt><dd>{{ trigger }}</dd></template>
              <dt>Impact</dt><dd>{{ impact }}</dd>
            </dl>
            <div :class="['conf', `conf--${conf.level}`]" role="note">
              <span class="conf__badge"><svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true">
                <circle v-if="conf.level === 'high'" cx="6" cy="6" r="5" fill="currentColor" />
                <path v-else-if="conf.level === 'medium'" d="M6 1a5 5 0 0 1 0 10z" fill="currentColor" />
                <circle v-else cx="6" cy="6" r="4.3" fill="none" stroke="currentColor" stroke-width="1.6" />
                <circle v-if="conf.level !== 'low'" cx="6" cy="6" r="5" fill="none" stroke="currentColor" stroke-width="1.2" /></svg>
                {{ conf.label }} <span class="conf__n">{{ Math.round((inc.confidence || 0) * 100) }}%</span></span>
              <span class="conf__advice">{{ conf.advice }}</span>
            </div>
            <p v-if="!inc.llm_ok" class="small unconf">Could not confirm with the model: this summary was assembled from the evidence below.</p>
            <p class="muted summary">{{ inc.summary }}</p>
            <p class="small dim">{{ inc.path === "known" ? "Matched a known problem from runbook memory" : `Written by ${inc.llm_model || "AI"}` }}, analysis took {{ dur((inc.analysis_ms || 0) / 1000) }}</p>
          </template>
          <UiWait v-else title="The AI is reading metrics, traces and logs…" />
        </UiCard>
        <UiCard v-if="evidence.length" title="Evidence" icon="list">
          <ul class="ev"><li v-for="(e, i) in evidence" :key="i"><span v-if="e.source" class="ev__src">{{ e.source }}</span>{{ e.text }}</li></ul>
          <div v-if="samples.length" class="row row--wrap mt-2 small"><span class="muted">Example traces</span>
            <UiButton v-for="t in samples" :key="t.trace_id" variant="tint" size="sm" @click="openTrace(t.trace_id)">{{ t.trace_id.slice(0, 8) }}</UiButton></div>
        </UiCard>
        <UiCard v-if="inc.runbook.length" title="Runbook" icon="book"><ol class="rb"><li v-for="(r, i) in inc.runbook" :key="i">{{ r }}</li></ol></UiCard>
        <UiDisclosure title="How the AI investigated" :meta="`${inc.steps.length} steps`"><InvestigationTimeline :steps="inc.steps" /></UiDisclosure>
      </div>
      <div class="stack sticky">
        <FixPanel :incident="inc" />
        <UiCard v-if="neighbours.length" title="Blast radius" icon="flowchart">
          <p class="small muted" style="margin:-2px 0 8px">Other machines RadarOps monitors on {{ inc.entity }}'s network — check these first if the cause is shared.</p>
          <router-link v-for="n in neighbours" :key="n.host" :to="`/computers/${n.host}`" class="nbr">
            <UiStatusDot tone="ok" :size="7" /><b>{{ n.host }}</b><span class="muted small">{{ n.networks.join(', ') }}{{ n.owner ? ` · ${n.owner}` : '' }}</span>
          </router-link>
        </UiCard>
      </div>
    </div>

    <!-- after-the-fact: feedback that trains the AI, and the incident's notification trail -->
    <div class="meta-row">
      <FeedbackCard :incident="inc" />
      <UiCard title="Notifications" icon="alert">
        <div v-for="n in inc.notifications" :key="n.id" class="small ntf"><UiStatusDot :tone="n.status && n.status.startsWith('sent') ? 'ok' : 'neutral'" :size="6" />{{ n.event.replace(/_/g, " ") }} · {{ clock(n.ts) }} · <span class="muted">{{ n.status }}</span></div>
        <p v-if="!inc.notifications.length" class="small muted">None sent</p>
        <div v-if="inc.status !== 'analyzing'" class="row row--wrap mt-2">
          <UiButton variant="tint" size="sm" icon="arrow_sync" @click="store.reanalyze(inc.id).catch((e) => ui.toast(e.message))">Run analysis again</UiButton>
          <UiButton v-if="!['resolved', 'closed', 'rejected'].includes(inc.status)" variant="plain" size="sm" @click="store.close(inc.id)">Close incident</UiButton>
        </div>
      </UiCard>
    </div>
    <UiSheet v-model="traceOpen" title="Request trace" :width="980"><TraceWaterfall :spans="trace || []" /></UiSheet>
  </div>
  <div v-else class="page"><UiPageHeader title="Loading…" :back="{ to: '/problems', label: 'Incidents' }" /></div>
</template>
<style scoped>
.rca { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 10px 14px; margin: 0; }
.rca dt { font-size: var(--fs-xs); font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.04em; color: var(--c-text-3); padding-top: 3px; }
.rca dd { margin: 0; font-size: var(--fs-sm); color: var(--c-text-2); }
.rca dd.rc { font-size: var(--fs-lg); font-weight: var(--fw-semibold); color: var(--c-text); line-height: 1.4; }
@media (max-width: 640px) { .rca { grid-template-columns: 1fr; gap: 2px; } .rca dd { margin-bottom: 8px; } }
.conf { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; margin-top: 14px; padding: 10px 12px; border-radius: var(--radius-md); background: var(--c-fill); font-size: var(--fs-sm); }
.conf__badge { display: inline-flex; align-items: center; gap: 6px; font-weight: var(--fw-semibold); }
.conf__n { font-weight: var(--fw-regular, 400); color: var(--c-text-3); font-variant-numeric: tabular-nums; }
.conf--high .conf__badge { color: var(--c-ok-text); } .conf--medium .conf__badge { color: var(--c-warn-text); } .conf--low .conf__badge { color: var(--c-bad-text); }
.conf__advice { color: var(--c-text-2); }
.unconf { margin-top: 8px; color: var(--c-warn-text); }
.facts { display: flex; flex-wrap: wrap; gap: 4px 20px; }
.facts b { font-weight: var(--fw-medium); color: var(--c-text); }
.summary { margin: 10px 0 12px; }
.ev { list-style: none; padding: 0; margin: 0; }
.ev li { padding: 8px 0 8px 16px; position: relative; border-top: 1px solid var(--c-separator); }
.ev li:first-child { border-top: 0; }
.ev li::before { content: ""; position: absolute; left: 0; top: 16px; width: 6px; height: 6px; border-radius: 1px; background: var(--c-primary); }
.ev__src { display: inline-block; margin-right: 8px; padding: 0 6px; border-radius: var(--radius-sm); background: var(--c-fill); font-size: 11px; font-weight: var(--fw-semibold); color: var(--c-text-2); line-height: 18px; vertical-align: 1px; }
.rb { margin: 0; padding-left: 20px; } .rb li { margin: 4px 0; }
.nbr { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-top: 1px solid var(--c-separator); color: var(--c-text); text-decoration: none; }
.nbr:first-of-type { border-top: 0; } .nbr:hover b { color: var(--c-primary); } .nbr b { font-weight: var(--fw-medium); font-size: var(--fs-sm); }
.nbr span { margin-left: auto; }
.sticky { position: sticky; top: 12px; }
.meta-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); margin-top: var(--sp-4); align-items: start; }
.ntf { display: flex; align-items: center; gap: 7px; padding: 2px 0; }
@media (max-width: 1080px) { .sticky { position: static; } .meta-row { grid-template-columns: 1fr; } }
</style>
