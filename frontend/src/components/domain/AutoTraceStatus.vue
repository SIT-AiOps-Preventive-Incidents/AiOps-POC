<script setup>
// "Connect a computer -> its services are traced for you": shows what the host agent's eBPF tracer is doing.
// host.auto_instrument = { state: running|starting|idle|unavailable|disabled|error, services[], error }
import { computed } from "vue";
const props = defineProps({ host: { type: Object, required: true }, services: { type: Array, default: () => [] } });
const st = computed(() => props.host.auto_instrument || null);
const traced = computed(() => props.services.filter((s) => s.instrumentation === "ebpf"));
const waiting = computed(() => (st.value?.services || []).filter((n) => !traced.value.some((s) => s.service === n)));
const mac = computed(() => /darwin|mac/i.test(props.host.os || ""));
const col = computed(() => st.value?.collector || null);
</script>
<template>
  <div class="auto" aria-live="polite">
    <!-- healthy: quiet one-line confirmations with a check, not a filled green banner -->
    <p v-if="col?.state === 'running'" class="line ok">
      <UiIcon name="checkmark_circle" filled :size="16" />Logs &amp; container metrics collected
      <span class="muted">· per-container CPU, memory, network via OpenTelemetry Collector</span></p>
    <p v-else-if="col?.state === 'starting'" class="line"><UiSpinner :size="14" />Starting log &amp; metric collection…</p>
    <p v-else-if="col?.error" class="line muted"><UiIcon name="alert" :size="15" />Logs: {{ col.error }}</p>

    <p v-if="st?.state === 'running' && !waiting.length && traced.length" class="line ok">
      <UiIcon name="checkmark_circle" filled :size="16" />Traced automatically
      <span class="muted">· {{ traced.length }} service{{ traced.length === 1 ? "" : "s" }} send traces with no code change (eBPF)</span></p>
    <p v-else-if="st && ['running', 'starting'].includes(st.state)" class="line"><UiSpinner :size="14" />Tracing the services found here…
      <span class="muted">watching {{ st.services.length }} port{{ st.services.length === 1 ? "" : "s" }} with eBPF<template v-if="waiting.length"> · each becomes traced after its first request: {{ waiting.join(", ") }}</template></span></p>

    <div v-else class="note">
      <UiIcon name="flash" :size="18" />
      <div>
        <b>{{ mac ? "Discovery only on macOS" : "Automatic tracing is off" }}</b>
        <p v-if="!st" class="small muted">This agent is older than 1.2. Run the install command again to update it.</p>
        <p v-else-if="st.state === 'idle'" class="small muted">No service with a web port was found yet. Tracing starts by itself when one appears.</p>
        <p v-else class="small muted">{{ st.error }}</p>
      </div>
    </div>
  </div>
</template>
<style scoped>
.line { display: flex; align-items: center; gap: 8px; font-size: var(--fs-sm); color: var(--c-text); padding: 4px 0; }
.line + .line { border-top: 1px solid var(--c-separator); }
.line .muted { font-weight: var(--fw-regular, 400); }
.line.ok > .ui-icon { color: var(--c-ok); }
.line.muted { color: var(--c-text-3); } .line.muted > .ui-icon { color: var(--c-text-3); }
.note { display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-radius: var(--radius-lg); background: var(--c-fill); color: var(--c-text-2); margin-top: 8px; }
.note b { color: var(--c-text); } .note p { margin: 2px 0 0; }
</style>
