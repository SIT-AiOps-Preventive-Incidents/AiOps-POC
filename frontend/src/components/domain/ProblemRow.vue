<script setup>
import { computed } from "vue";
import { ago } from "@/lib/format";
import { INCIDENT_KIND } from "@/lib/vocab";
import StatusPill from "./StatusPill.vue";
const props = defineProps({ incident: { type: Object, required: true } });
const kind = computed(() => INCIDENT_KIND[props.incident.kind] || { icon: "warning", color: "var(--c-text-3)" });
</script>
<template>
  <UiListRow :to="`/problems/${incident.id}`" :title="incident.title" :detail="incident.root_cause || undefined"
             :subtitle="`P-${incident.id} · ${incident.entity} · ${ago(incident.detected_at)}${incident.owner ? ' · ' + incident.owner : ''}`">
    <template #leading><UiAppTile :icon="kind.icon" :color="kind.color" /></template>
    <template #accessory><StatusPill :status="incident.status" /></template>
  </UiListRow>
</template>
