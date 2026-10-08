<script setup>
import { computed } from "vue";
import { ago, ms, num, pct } from "@/lib/format";
import { HEALTH_TONE, kindIcon, languageLogo } from "@/lib/vocab";
const props = defineProps({ service: { type: Object, required: true } });
const s = computed(() => props.service);
const subtitle = computed(() => {
  if (s.value.kind === "process" || s.value.kind === "external")
    return `${s.value.kind === "external" ? "External" : "Discovered"} on ${s.value.hosts.join(", ") || "-"} · seen ${ago(s.value.last_seen)}`;
  const auto = s.value.instrumentation === "ebpf" ? "Traced automatically · " : "";
  if (s.value.status === "no-data") return `${auto}Waiting for data`;
  return `${auto}${s.value.version ? `v${s.value.version} · ` : ""}${num(s.value.rps)} req/s · p95 ${ms(s.value.p95_ms)}`;
});
</script>
<template>
  <UiListRow :to="`/services/${s.service}`" :title="s.name" :subtitle="subtitle">
    <template #leading><UiAppTile :logo="languageLogo(s.language || s.service)" :icon="kindIcon(s.kind)" :status="HEALTH_TONE[s.status]" /></template>
    <template #accessory>
      <UiPill v-if="s.problem_id" tone="bad">Problem</UiPill>
      <span v-else-if="s.error_rate != null" :class="{ bad: s.error_rate > 0.05 }">{{ pct(s.error_rate) }} errors</span>
    </template>
  </UiListRow>
</template>
