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
import { useIncidentStore } from "@/stores/incidents";
import { useUiStore } from "@/stores/ui";
import { ref } from "vue";

const props = defineProps({ id: String });
const store = useIncidentStore();
const ui = useUiStore();
const inc = computed(() => store.byId[props.id]);
usePolling(() => store.load(props.id), 4000);

const steps = computed(() => {
  const i = inc.value;
  if (!i) return [];
  const ex = i.approval?.execution;
  const s = [
    { label: "Detected", ts: i.detected_at, done: true },
    { label: "AI investigated", ts: i.analyzed_at, done: !!i.analyzed_at },
    { label: "Your approval", ts: i.approval?.decision === "approved" ? i.approval.decided_at : null, done: i.approval?.decision === "approved", you: true },
    { label: "Fix applied", ts: ex?.ok ? ex.executed_at : null, done: !!ex?.ok },
    { label: "Verified", ts: i.status === "resolved" ? i.resolved_at : null, done: i.status === "resolved" },
  ];
  const now = s.findIndex((x) => !x.done);
  const failed = ["remediation_failed", "rejected"].includes(i.status);
  return s.map((x, k) => ({ label: x.label, time: clock(x.ts), state: x.done ? "done" : k === now ? (failed ? "failed" : x.you ? "you" : "current") : "todo" }));
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
        <UiCard title="What happened">
          <template v-if="inc.root_cause">
            <p class="rc">{{ inc.root_cause }}</p>
            <p v-if="trigger" class="trig">{{ trigger }}</p>
            <p class="muted summary">{{ inc.summary }}</p>
            <div class="row small"><span class="muted">AI confidence</span><div class="conf"><div :style="{ width: `${(inc.confidence || 0) * 100}%` }" /></div><b>{{ Math.round((inc.confidence || 0) * 100) }}%</b></div>
            <p class="small dim mt-2">{{ inc.path === "known" ? "Matched a known problem from runbook memory" : `Written by ${inc.llm_model || "AI"}${inc.llm_ok ? "" : " (from evidence)"}` }}, analysis took {{ dur((inc.analysis_ms || 0) / 1000) }}</p>
          </template>
          <UiWait v-else title="The AI is reading metrics, traces and logs…" />
        </UiCard>
        <UiCard v-if="inc.evidence.length" title="Evidence">
          <ul class="ev"><li v-for="(e, i) in inc.evidence" :key="i">{{ e }}</li></ul>
          <div v-if="samples.length" class="row row--wrap mt-2 small"><span class="muted">Example traces</span>
            <UiButton v-for="t in samples" :key="t.trace_id" variant="tint" size="sm" @click="openTrace(t.trace_id)">{{ t.trace_id.slice(0, 8) }}</UiButton></div>
        </UiCard>
        <UiCard v-if="inc.runbook.length" title="Runbook"><ol class="rb"><li v-for="(r, i) in inc.runbook" :key="i">{{ r }}</li></ol></UiCard>
        <UiDisclosure title="How the AI investigated" :meta="`${inc.steps.length} steps`"><InvestigationTimeline :steps="inc.steps" /></UiDisclosure>
      </div>
      <div class="stack sticky">
        <FixPanel :incident="inc" />
        <FeedbackCard :incident="inc" />
        <UiCard title="Notifications">
          <div v-for="n in inc.notifications" :key="n.id" class="small">{{ n.event.replace(/_/g, " ") }} · {{ clock(n.ts) }} · <span class="muted">{{ n.status }}</span></div>
          <p v-if="!inc.notifications.length" class="small muted">None sent</p>
          <div v-if="inc.status !== 'analyzing'" class="row row--wrap mt-2">
            <UiButton variant="plain" size="sm" @click="store.reanalyze(inc.id).catch((e) => ui.toast(e.message))">Run analysis again</UiButton>
            <UiButton v-if="!['resolved', 'closed', 'rejected'].includes(inc.status)" variant="plain" size="sm" @click="store.close(inc.id)">Close incident</UiButton>
          </div>
        </UiCard>
      </div>
    </div>
    <UiSheet v-model="traceOpen" title="Request trace" :width="980"><TraceWaterfall :spans="trace || []" /></UiSheet>
  </div>
  <div v-else class="page"><UiPageHeader title="Loading…" :back="{ to: '/problems', label: 'Incidents' }" /></div>
</template>
<style scoped>
.rc { font-size: var(--fs-xl); font-weight: var(--fw-semibold); line-height: 1.4; }
.trig { margin-top: 10px; padding: 8px 12px; border-radius: var(--radius-md); background: var(--c-fill); font-size: var(--fs-sm); color: var(--c-text-2); }
.facts { display: flex; flex-wrap: wrap; gap: 4px 20px; }
.facts b { font-weight: var(--fw-medium); color: var(--c-text); }
.summary { margin: 10px 0 12px; }
.conf { flex: 1; height: 4px; background: var(--c-fill-2); border-radius: 2px; overflow: hidden; }
.conf div { height: 100%; background: var(--c-primary); border-radius: 3px; }
.ev { list-style: none; padding: 0; margin: 0; }
.ev li { padding: 8px 0 8px 16px; position: relative; border-top: 1px solid var(--c-separator); }
.ev li:first-child { border-top: 0; }
.ev li::before { content: ""; position: absolute; left: 0; top: 16px; width: 6px; height: 6px; border-radius: 1px; background: var(--c-primary); }
.rb { margin: 0; padding-left: 20px; } .rb li { margin: 4px 0; }
.sticky { position: sticky; top: 12px; }
@media (max-width: 1080px) { .sticky { position: static; } }
</style>
