<script setup>
// A service in a list: its real logo (or a drawn glyph for its kind), how it is watched, its traffic, and its health.
import { computed } from "vue";
import { ago, ms, pct, rate } from "@/lib/format";
import { HEALTH_TONE, languageLogo } from "@/lib/vocab";
const props = defineProps({ service: { type: Object, required: true } });
const s = computed(() => props.service);
const GLYPH = { network: "router", process: "process", external: "globe", client: "globe" };
const discovered = computed(() => s.value.kind === "process" || s.value.kind === "external");
const subtitle = computed(() => {
  if (discovered.value) return `${s.value.kind === "external" ? "External" : "Discovered"} on ${s.value.hosts.join(", ") || "-"}`;
  const how = { ebpf: "Traced automatically", check: "Checked from outside" }[s.value.instrumentation] || "OpenTelemetry";
  return `${how}${s.value.version ? ` · v${s.value.version}` : ""}`;
});
const meta = computed(() => (discovered.value ? `seen ${ago(s.value.last_seen)}`
  : s.value.status === "no-data" ? "no traffic yet" : `${rate(s.value.rps)} · p95 ${ms(s.value.p95_ms)}`));
const health = computed(() => {
  if (s.value.problem_id) return { tone: "bad", label: "Problem", value: `P-${s.value.problem_id} open` };
  if (discovered.value) return { tone: "neutral", label: "Discovered" };
  if (s.value.status === "no-data") return { tone: "neutral", label: "Waiting for data" };
  return { tone: s.value.error_rate > 0.05 ? "warn" : "ok", label: s.value.error_rate > 0.05 ? "Errors up" : "Healthy",
    value: s.value.error_rate != null ? `${pct(s.value.error_rate)} errors` : undefined };
});
</script>
<template>
  <UiResourceRow :to="`/services/${s.service}`" :title="s.name" :subtitle="subtitle" :meta="meta"
                 :logo="languageLogo(s.language || s.service)" :glyph="GLYPH[s.kind] || 'service'" :tone="HEALTH_TONE[s.status]">
    <UiHealth :tone="health.tone" :label="health.label" :value="health.value" />
  </UiResourceRow>
</template>
