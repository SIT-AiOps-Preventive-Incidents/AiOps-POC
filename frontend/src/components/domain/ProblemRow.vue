<script setup>
// One incident in a list: a drawing of what broke, the AI's finding, how loud it is, and how far along the fix is.
import { computed } from "vue";
import { ago } from "@/lib/format";
import { INCIDENT_KIND } from "@/lib/vocab";
import SeverityPill from "./SeverityPill.vue";
import StatusPill from "./StatusPill.vue";
const props = defineProps({ incident: { type: Object, required: true } });
const kind = computed(() => INCIDENT_KIND[props.incident.kind] || { glyph: "inc_error", label: props.incident.title });
const entity = computed(() => props.incident.entity_name || props.incident.entity);
</script>
<template>
  <router-link :to="`/problems/${incident.id}`" :class="['pr', { 'pr--yours': incident.status === 'awaiting_approval' }]" role="listitem">
    <span class="pr__ic"><UiGlyph :name="kind.glyph || 'inc_error'" :size="30" /></span>
    <span class="pr__main">
      <span class="pr__title"><b>{{ kind.label }}</b> <span class="pr__on">on</span> {{ entity }}</span>
      <span v-if="incident.root_cause" class="pr__rc">{{ incident.root_cause }}</span>
      <span class="pr__meta">P-{{ incident.id }} · {{ ago(incident.detected_at) }}</span>
    </span>
    <SeverityPill :severity="incident.severity" />
    <StatusPill :status="incident.status" />
    <UiIcon name="chevron_right" :size="16" class="pr__go" />
  </router-link>
</template>
<style scoped>
.pr { display: grid; grid-template-columns: 46px minmax(0, 1fr) 96px 120px 18px; align-items: center; gap: 18px; padding: 16px 20px; color: var(--c-text);
  position: relative; transition: background var(--dur-fast) var(--ease); }
.pr:hover { background: var(--c-hover); }
.pr:hover .pr__go { color: var(--c-text); transform: translateX(2px); }
/* your turn: a thin mint edge on the left, nothing louder */
.pr--yours::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 3px; border-radius: 0 3px 3px 0; background: var(--c-action); }
.pr__ic { width: 46px; height: 46px; border-radius: 14px; display: grid; place-items: center; background: var(--c-fill);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05); }
.pr__main { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.pr__title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 15px; }
.pr__title b { font-weight: var(--fw-semibold); } .pr__on { color: var(--c-text-3); }
.pr__rc { font-size: var(--fs-sm); color: var(--c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pr__meta { font-size: var(--fs-xs); color: var(--c-text-3); font-variant-numeric: tabular-nums; }
.pr__go { color: var(--c-text-3); transition: transform var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
@media (max-width: 760px) { .pr { grid-template-columns: 40px minmax(0, 1fr) auto; gap: 12px; } .pr .sev, .pr__go { display: none; } .pr__ic { width: 40px; height: 40px; } }
</style>
