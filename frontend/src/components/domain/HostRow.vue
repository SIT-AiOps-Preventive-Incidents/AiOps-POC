<script setup>
import { computed } from "vue";
import { HEALTH_TONE, osLogo } from "@/lib/vocab";
const props = defineProps({ host: { type: Object, required: true } });
const line = computed(() => {
  const h = props.host;
  if (h.status === "offline") return "Offline";
  if (h.status === "no-data") return "Waiting for first data";
  return `CPU ${Math.round(h.cpu)}% · Memory ${Math.round(h.mem)}% · Disk ${Math.round(h.disk)}%${h.services?.length ? ` · ${h.services.length} services` : ""}`;
});
</script>
<template>
  <UiListRow :to="`/computers/${host.name}`" :title="host.name" :subtitle="line">
    <template #leading><UiAppTile :logo="osLogo(host.os)" :icon="host.kind === 'workstation' ? 'laptop' : 'server'" :status="HEALTH_TONE[host.status]" /></template>
    <template #accessory><UiPill v-if="host.problem_id" tone="bad">Problem</UiPill></template>
  </UiListRow>
</template>
