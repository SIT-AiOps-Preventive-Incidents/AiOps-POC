<script setup>
// One incident in a list: what broke and the AI's finding on the left, where/how bad/where it is on the right.
import { computed } from "vue";
import { ago } from "@/lib/format";
import { INCIDENT_KIND } from "@/lib/vocab";
import SeverityPill from "./SeverityPill.vue";
import StatusPill from "./StatusPill.vue";
const props = defineProps({ incident: { type: Object, required: true } });
const kind = computed(() => INCIDENT_KIND[props.incident.kind] || { icon: "warning", label: props.incident.title });
const entity = computed(() => props.incident.entity_name || props.incident.entity);
</script>
<template>
  <router-link :to="`/problems/${incident.id}`" class="pr" role="listitem">
    <span class="pr__ic"><UiIcon :name="kind.icon" :size="16" /></span>
    <span class="pr__main">
      <span class="pr__title"><b>{{ kind.label }}</b> on {{ entity }}</span>
      <span v-if="incident.root_cause" class="pr__rc">{{ incident.root_cause }}</span>
    </span>
    <span class="pr__id">P-{{ incident.id }}</span>
    <SeverityPill :severity="incident.severity" />
    <StatusPill :status="incident.status" class="pr__st" />
    <span class="pr__ago">{{ ago(incident.detected_at) }}</span>
  </router-link>
</template>
<style scoped>
.pr { display: grid; grid-template-columns: 28px minmax(0, 1fr) 48px 64px 120px 80px; align-items: center; gap: 12px; padding: 10px 16px; color: var(--c-text); }
.pr:hover { background: var(--c-hover); }
.pr__ic { width: 28px; height: 28px; border-radius: var(--radius-md); background: var(--c-fill); color: var(--c-text-2); display: grid; place-items: center; }
.pr__main { min-width: 0; display: flex; flex-direction: column; }
.pr__title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pr__title b { font-weight: var(--fw-semibold); }
.pr__rc { font-size: var(--fs-sm); color: var(--c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pr__id { font-family: var(--font-mono); font-size: var(--fs-xs); color: var(--c-text-3); }
.pr > .ui-pill { justify-self: start; }
.pr__ago { font-size: var(--fs-sm); color: var(--c-text-3); text-align: right; white-space: nowrap; }
@media (max-width: 760px) { .pr { grid-template-columns: 28px minmax(0, 1fr) auto; } .pr__id, .pr__ago, .pr .ui-pill:first-of-type { display: none; } }
</style>
