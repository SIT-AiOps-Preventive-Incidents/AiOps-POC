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
    { label: "Analyzed", ts: i.analyzed_at, done: !!i.analyzed_at },
    { label: "Approved", ts: i.approval?.decision === "approved" ? i.approval.decided_at : null, done: i.approval?.decision === "approved" },
    { label: "Fixed", ts: ex?.ok ? ex.executed_at : null, done: !!ex?.ok },
    { label: "Verified", ts: i.status === "resolved" ? i.resolved_at : null, done: i.status === "resolved" },
  ];
  const now = s.findIndex((x) => !x.done);
  const failed = ["remediation_failed", "rejected"].includes(i.status);
  return s.map((x, k) => ({ label: x.label, time: clock(x.ts), state: x.done ? "done" : k === now ? (failed ? "failed" : "current") : "todo" }));
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
    <UiPageHeader :title="inc.title" :back="{ to: '/problems', label: 'Problems' }">
      <template #subtitle>{{ inc.entity_type === "host" ? "Computer" : "Service" }} <b>{{ inc.entity }}</b>
        <span v-if="inc.affected.length"> · also affected {{ inc.affected.join(", ") }}</span> · detected {{ clockSec(inc.detected_at) }} · owner {{ inc.owner || "-" }}</template>
      <SeverityPill :severity="inc.severity" /><StatusPill :status="inc.status" />
    </UiPageHeader>
    <UiStepper :steps="steps" />
    <div class="split mt">
      <div class="stack">
        <UiCard title="What happened">
          <template v-if="inc.root_cause">
            <p class="rc">{{ inc.root_cause }}</p>
            <p class="muted summary">{{ inc.summary }}</p>
            <div class="row small"><span class="muted">AI confidence</span><div class="conf"><div :style="{ width: `${(inc.confidence || 0) * 100}%` }" /></div><b>{{ Math.round((inc.confidence || 0) * 100) }}%</b></div>
            <p class="small dim mt-2">{{ inc.path === "known" ? "Matched a known problem from runbook memory" : `Written by ${inc.llm_model || "AI"}${inc.llm_ok ? "" : " (from evidence)"}` }} · analysis took {{ dur((inc.analysis_ms || 0) / 1000) }}</p>
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
            <UiButton v-if="!['resolved', 'closed', 'rejected'].includes(inc.status)" variant="plain" size="sm" @click="store.close(inc.id)">Close problem</UiButton>
          </div>
        </UiCard>
      </div>
    </div>
    <UiSheet v-model="traceOpen" title="Request trace" :width="980"><TraceWaterfall :spans="trace || []" /></UiSheet>
  </div>
  <div v-else class="page"><UiPageHeader title="Loading…" :back="{ to: '/problems', label: 'Problems' }" /></div>
</template>
<style scoped>
.rc { font-size: 19px; font-weight: var(--fw-semibold); line-height: 1.35; letter-spacing: -0.01em; }
.summary { margin: 10px 0 12px; }
.conf { flex: 1; height: 6px; background: var(--c-fill-2); border-radius: 3px; overflow: hidden; }
.conf div { height: 100%; background: var(--c-primary); border-radius: 3px; }
.ev { list-style: none; padding: 0; margin: 0; }
.ev li { padding: 9px 0 9px 16px; position: relative; border-top: 0.5px solid var(--c-separator); font-size: 14.5px; }
.ev li:first-child { border-top: 0; }
.ev li::before { content: ""; position: absolute; left: 0; top: 17px; width: 6px; height: 6px; border-radius: 50%; background: var(--c-primary); }
.rb { margin: 0; padding-left: 20px; } .rb li { margin: 4px 0; }
.sticky { position: sticky; top: 12px; }
@media (max-width: 1080px) { .sticky { position: static; } }
</style>
