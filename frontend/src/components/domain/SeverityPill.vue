<script setup>
// Severity as a signal: three rising bars, lit by how loud the incident is, and the word beside them.
// Not a coloured badge - the bars carry the level even without colour, the word says it plainly.
import { computed } from "vue";
import { SEVERITY } from "@/lib/stage";
const props = defineProps({ severity: String });
const s = computed(() => SEVERITY[props.severity] || SEVERITY.minor);
</script>
<template>
  <span :class="['sev', `sev--${severity || 'minor'}`]" :aria-label="`Severity: ${s.label}`">
    <svg viewBox="0 0 14 12" width="14" height="12" aria-hidden="true">
      <rect x="0" y="7" width="3.2" height="5" rx="1" :class="{ on: s.level >= 1 }" />
      <rect x="5.4" y="4" width="3.2" height="8" rx="1" :class="{ on: s.level >= 2 }" />
      <rect x="10.8" y="0" width="3.2" height="12" rx="1" :class="{ on: s.level >= 3 }" />
    </svg>
    {{ s.label }}
  </span>
</template>
<style scoped>
.sev { display: inline-flex; align-items: center; gap: 7px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); white-space: nowrap; }
rect { fill: var(--c-fill-2); }
.sev--critical rect.on { fill: var(--c-bad); } .sev--critical { color: var(--c-bad-text); }
.sev--major rect.on { fill: var(--c-warn); }
.sev--minor rect.on { fill: var(--c-text-3); }
</style>
