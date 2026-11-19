<script setup>
// A host in a list: a drawn machine (or its OS logo), its load as three small numbers, and its health.
import { computed } from "vue";
import { HEALTH_TONE, osLogo } from "@/lib/vocab";
const props = defineProps({ host: { type: Object, required: true } });
const h = computed(() => props.host);
const line = computed(() => (h.value.status === "offline" ? "Offline" : h.value.status === "no-data" ? "Waiting for first data"
  : `CPU ${Math.round(h.value.cpu)}% · Memory ${Math.round(h.value.mem)}% · Disk ${Math.round(h.value.disk)}%`));
const health = computed(() => (h.value.problem_id ? { tone: "bad", label: "Problem", value: `P-${h.value.problem_id} open` }
  : { tone: HEALTH_TONE[h.value.status] || "neutral", label: { healthy: "Healthy", offline: "Offline", "no-data": "Waiting", down: "Down" }[h.value.status] || h.value.status }));
</script>
<template>
  <UiResourceRow :to="`/computers/${h.name}`" :title="h.name" :subtitle="line" :meta="h.services?.length ? `${h.services.length} services` : undefined"
                 :logo="osLogo(h.os)" :glyph="h.kind === 'workstation' ? 'laptop' : 'server'" :tone="HEALTH_TONE[h.status]">
    <UiHealth :tone="health.tone" :label="health.label" :value="health.value" />
  </UiResourceRow>
</template>
