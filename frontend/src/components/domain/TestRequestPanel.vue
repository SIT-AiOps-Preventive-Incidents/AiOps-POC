<script setup>
// Result of a test request: status, total time, and the hop list in sync with the map animation.
import { computed } from "vue";
import { ms } from "@/lib/format";
import { useMapStore } from "@/stores/map";
import TraceWaterfall from "./TraceWaterfall.vue";
const map = useMapStore();
const t = computed(() => map.test);
const total = computed(() => t.value.run?.duration_ms);
const errored = computed(() => t.value.hops.some((h) => h.error) || (t.value.run?.http_status || 0) >= 500);
</script>
<template>
  <UiCard v-if="t.phase !== 'idle'" title="Test request">
    <template #actions><UiButton variant="plain" size="sm" @click="map.resetTest()">Clear</UiButton></template>
    <UiWait v-if="t.phase === 'sending'" title="Sending a request" subtitle="Through the firewall and load balancer like a real user" />
    <UiWait v-else-if="t.phase === 'tracing'" title="Waiting for the trace" :subtitle="`HTTP ${t.run?.http_status} in ${ms(t.run?.duration_ms)} · collecting spans from every hop...`" />
    <div v-else-if="t.phase === 'error'" class="bad">{{ t.error }}</div>
    <template v-else>
      <div class="summary">
        <UiPill :tone="errored ? 'bad' : 'ok'">HTTP {{ t.run?.http_status }}</UiPill>
        <span><b>{{ ms(total) }}</b> end to end · {{ t.hops.length }} hops</span>
        <span class="mono dim">{{ t.run?.id?.slice(0, 12) }}</span>
      </div>
      <ol class="hops">
        <li v-for="(h, i) in t.hops" :key="i" :class="{ now: t.phase === 'playing' && i === t.step, done: t.phase === 'done' || i < t.step, bad: h.error }">
          <span class="n">{{ i + 1 }}</span>
          <span class="hop"><b>{{ h.from === "clients" ? "Clients" : h.fromInstance || h.from }}</b> → <b>{{ h.instance || h.to }}</b>
            <span class="muted small block">{{ h.name }}</span><span v-if="h.error && h.message" class="small bad block">{{ h.message }}</span></span>
          <span class="t">{{ ms(h.duration) }}</span>
        </li>
      </ol>
      <UiDisclosure :card="false" title="Full trace (every span)"><TraceWaterfall :spans="t.run?.spans || []" /></UiDisclosure>
    </template>
  </UiCard>
</template>
<style scoped>
.summary { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.hops { list-style: none; padding: 0; margin: 12px 0; display: flex; flex-direction: column; gap: 2px; }
.hops li { display: grid; grid-template-columns: 24px minmax(0, 1fr) 70px; gap: 8px; align-items: center; padding: 7px 8px; border-radius: 8px; font-size: 14px; color: var(--c-text-3); transition: background var(--dur); }
.hops li.done, .hops li.now { color: var(--c-text); }
.hops li.now { background: var(--c-primary-tint); }
.hops li.bad.done { background: var(--c-bad-bg); }
.n { width: 22px; height: 22px; border-radius: 50%; background: var(--c-fill-2); display: grid; place-items: center; font-size: 12px; font-weight: 700; }
.done .n, .now .n { background: var(--c-primary); color: #fff; }
.bad.done .n { background: var(--c-bad); }
.hop { min-width: 0; }
.t { text-align: right; font-variant-numeric: tabular-nums; }
.block { display: block; }
</style>
