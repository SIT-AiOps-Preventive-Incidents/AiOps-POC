<script setup>
// One open incident in the action queue: what broke, what the AI found, and where it is in the
// detect -> investigate -> approve -> fix -> verify lifecycle. Orange marks the step that needs a person.
import { computed } from "vue";
import { ago } from "@/lib/format";
import { INCIDENT_KIND } from "@/lib/vocab";
import { useI18n } from "@/lib/i18n";
import SeverityPill from "./SeverityPill.vue";

const props = defineProps({ incident: { type: Object, required: true } });
const { t } = useI18n();
const i = computed(() => props.incident);
const kind = computed(() => INCIDENT_KIND[i.value.kind] || { icon: "warning", label: "Problem" });
const entity = computed(() => i.value.entity_name || i.value.entity);

const STAGES = computed(() => [t("Detected", "ตรวจพบ"), t("AI investigated", "AI สืบสวน"), t("Your approval", "คุณอนุมัติ"), t("Fix applied", "แก้ไขแล้ว"), t("Verified", "ยืนยันแล้ว")]);
const AT = { open: 1, analyzing: 1, awaiting_approval: 2, remediating: 3, verifying: 4, remediation_failed: 3 };
const stages = computed(() => {
  const at = AT[i.value.status] ?? 1;
  const failed = i.value.status === "remediation_failed";
  return STAGES.value.map((label, k) => ({
    label, state: k < at ? "done" : k === at ? (failed ? "failed" : at === 2 ? "you" : "now") : "todo",
  }));
});
const waiting = computed(() => i.value.status === "awaiting_approval");
</script>
<template>
  <article :class="['inc', { 'inc--you': waiting }]">
    <header class="inc__head">
      <span class="inc__kind"><UiIcon :name="kind.icon" :size="16" /></span>
      <div class="inc__title">
        <router-link :to="`/problems/${i.id}`"><b>{{ kind.label || i.title }}</b> {{ t("on", "ที่") }} {{ entity }}</router-link>
        <span class="inc__meta">P-{{ i.id }} · {{ t("detected", "ตรวจพบ") }} {{ ago(i.detected_at) }}<template v-if="i.owner"> · {{ t("owner", "เจ้าของ") }} {{ i.owner }}</template></span>
      </div>
      <SeverityPill :severity="i.severity" />
      <UiButton v-if="waiting" variant="action" :to="`/problems/${i.id}`">{{ t("Review fix", "ดูการแก้ไข") }}</UiButton>
      <UiButton v-else variant="tint" :to="`/problems/${i.id}`">{{ t("Open", "เปิด") }}</UiButton>
    </header>
    <p v-if="i.root_cause" class="inc__rc"><span class="inc__ai">{{ t("AI found", "AI พบ") }}</span>{{ i.root_cause }}</p>
    <p v-else class="inc__rc inc__rc--wait"><UiSpinner :size="14" />{{ t("The AI is reading the metrics, traces and logs for", "AI กำลังอ่าน metric, trace และ log ของ") }} {{ entity }}.</p>
    <ol class="life" aria-label="Incident progress">
      <li v-for="s in stages" :key="s.label" :class="s.state" :aria-current="['now', 'you'].includes(s.state) ? 'step' : undefined">{{ s.label }}</li>
    </ol>
  </article>
</template>
<style scoped>
.inc { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 14px 16px; }
.inc--you { box-shadow: inset 3px 0 0 var(--c-action); }
.inc__head { display: flex; align-items: center; gap: 10px; }
.inc__head .ui-button { flex: none; }
.inc__kind { width: 28px; height: 28px; border-radius: var(--radius-md); display: grid; place-items: center; flex: none; background: var(--c-fill); color: var(--c-text-2); }
.inc__title { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.inc__title a { color: var(--c-text); font-size: var(--fs-lg); }
.inc__title a:hover { color: var(--c-primary); }
.inc__title b { font-weight: var(--fw-semibold); }
.inc__meta { font-size: var(--fs-sm); color: var(--c-text-3); }
.inc__rc { margin: 10px 0 0 38px; color: var(--c-text); max-width: 90ch; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.inc__rc--wait { display: flex; align-items: center; gap: 8px; color: var(--c-text-2); }
.inc__ai { color: var(--c-primary); font-weight: var(--fw-semibold); margin-right: 8px; }
.life { display: flex; list-style: none; margin: 12px 0 0 38px; padding: 0; gap: 4px; flex-wrap: wrap; font-size: var(--fs-xs); font-weight: var(--fw-medium); }
.life li { display: flex; align-items: center; gap: 6px; padding: 3px 8px 3px 6px; border-radius: var(--radius-sm); color: var(--c-text-3); background: var(--c-fill); }
.life li::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.5; }
.life li.done { color: var(--c-text-2); }
.life li.done::before { background: var(--c-ok); opacity: 1; }
.life li.now { color: var(--c-primary); background: var(--c-primary-tint); }
.life li.now::before { opacity: 1; animation: blink 1.4s ease-in-out infinite; }
.life li.you { color: var(--c-on-action); background: var(--c-action); }
.life li.you::before { background: var(--c-on-action); opacity: 1; }
.life li.failed { color: var(--c-bad-text); background: var(--c-bad-bg); }
.life li.failed::before { opacity: 1; }
@keyframes blink { 50% { opacity: 0.25; } }
@media (max-width: 760px) { .inc__rc, .life { margin-left: 0; } }
</style>
