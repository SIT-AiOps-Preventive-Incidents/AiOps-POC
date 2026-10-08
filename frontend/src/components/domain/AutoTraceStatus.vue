<script setup>
// "Connect a computer -> its services are traced for you": shows what the host agent's eBPF tracer is doing.
// host.auto_instrument = { state: running|starting|idle|unavailable|disabled|error, services[], error }
import { computed } from "vue";
const props = defineProps({ host: { type: Object, required: true }, services: { type: Array, default: () => [] } });
const st = computed(() => props.host.auto_instrument || null);
const traced = computed(() => props.services.filter((s) => s.instrumentation === "ebpf"));
const waiting = computed(() => (st.value?.services || []).filter((n) => !traced.value.some((s) => s.service === n)));
const mac = computed(() => /darwin|mac/i.test(props.host.os || ""));
</script>
<template>
  <div class="auto" aria-live="polite">
    <UiWait v-if="st?.state === 'running' && !waiting.length && traced.length" done title="Traced automatically">
      {{ traced.length }} service{{ traced.length === 1 ? "" : "s" }} on this computer send traces with no code change (eBPF).
    </UiWait>
    <UiWait v-else-if="st && ['running', 'starting'].includes(st.state)" title="Tracing the services found here…">
      Watching {{ st.services.length }} port{{ st.services.length === 1 ? "" : "s" }} with eBPF.
      <template v-if="waiting.length"> Each service turns into a traced service after its first request: {{ waiting.join(", ") }}.</template>
    </UiWait>
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
.note { display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px; border-radius: 12px; background: var(--c-fill); color: var(--c-text-2); }
.note b { color: var(--c-text); }
.note p { margin: 2px 0 0; }
</style>
