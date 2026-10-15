<script setup>
import { ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ms, slug } from "@/lib/format";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const step = ref(1);
const svc = ref("");
const url = ref("");
const owner = ref(ui.prefs.lastOwner || "");
const busy = ref(false);
const checks = ref([]);
const every = ref(10);
const status = ref(null);

async function start() {
  svc.value = slug(svc.value);
  if (!svc.value) return ui.toast("Enter a name");
  if (!/^https?:\/\/\S+$/.test(url.value.trim())) return ui.toast("Enter an address that starts with http:// or https://");
  ui.setPref("lastOwner", owner.value);
  busy.value = true;
  try {
    const r = await api.checks.create({ service_name: svc.value, url: url.value.trim(), owner: owner.value || "unassigned" });
    checks.value = [r.first_check];
    every.value = r.every_s;
    step.value = 2;
  } catch (e) {
    ui.toast(e.message);
  } finally {
    busy.value = false;
  }
}
usePolling(async () => {
  if (step.value < 2) return;
  checks.value = (await api.checks.recent(svc.value)).checks;
  status.value = await api.services.telemetry(svc.value);
  if (status.value.metrics && status.value.traces) step.value = 3;
}, 4000);
const clock = (ts) => new Date(ts * 1000).toLocaleTimeString([], { hour12: false });
const tone = (c) => (c.state === "ok" ? "ok" : "bad");
const answer = (c) => (c.status ? `HTTP ${c.status}` : c.error);
const ok = (b) => (b ? "ok" : "neutral");
</script>
<template>
  <div class="page page--narrow">
    <UiPageHeader title="Watch a website or system" :back="{ to: '/connect', label: 'Add a host or service' }"
                  subtitle="For systems you cannot install anything on. RadarOps calls the address like a browser would and learns its normal response time." />
    <ol class="steps">
      <li :class="['step', { done: step > 1 }]"><span class="n">1</span><div class="body"><h2>Which system?</h2>
        <template v-if="step === 1">
          <UiField v-model="svc" label="Name" placeholder="esg360" />
          <UiField v-model="url" label="Address" placeholder="https://34.2.129.3:3000/" />
          <UiField v-model="owner" label="Owner team" hint="(gets the problems)" placeholder="team-esg" @enter="start" />
          <UiButton class="mt" :disabled="busy" @click="start">{{ busy ? "Checking…" : "Start checking" }}</UiButton>
        </template>
        <div v-else><b>{{ svc }}</b> <span class="muted">· {{ url }} · owner {{ owner || "unassigned" }}</span></div></div></li>
      <li :class="['step', { done: step > 2, todo: step < 2 }]"><span class="n">2</span><div class="body"><h2>Checks every {{ every }} s</h2>
        <template v-if="step >= 2">
          <UiList plain>
            <UiListRow v-for="c in checks.slice(0, 6)" :key="c.trace_id" :title="`${answer(c)} in ${ms(c.ms)}`"
                       :subtitle="`${clock(c.start)}${c.final_url && c.final_url !== c.url ? ` · ended at ${c.final_url}` : ''}${c.cert_days_left != null ? ` · certificate valid ${c.cert_days_left} more days` : ''}`">
              <template #accessory><UiPill :tone="tone(c)">{{ c.state === "ok" ? "Answered" : "Failed" }}</UiPill></template>
            </UiListRow>
          </UiList>
          <p class="small muted mt-2">Nothing is installed on the system. A reply of 500 or above, no reply, or an invalid certificate counts as a failed check.</p>
        </template><p v-else class="small muted">Starts after step 1.</p></div></li>
      <li :class="['step', { done: step === 3, todo: step < 2 }]"><span class="n">3</span><div class="body"><h2>Check the data arrives</h2>
        <UiWait v-if="step === 2" title="Waiting for the first minute of data…" subtitle="Response time and errors need about a minute of checks." />
        <template v-else-if="step === 3">
          <UiWait done :title="`${svc} is being watched`"><span class="row row--wrap mt-2"><UiPill :tone="ok(status?.traces)">traces</UiPill><UiPill :tone="ok(status?.metrics)">metrics</UiPill><UiPill :tone="ok(status?.logs)">logs</UiPill></span></UiWait>
          <div class="row mt"><UiButton :to="`/services/${svc}`">Open {{ svc }}</UiButton><UiButton variant="tint" to="/services">All services</UiButton></div>
        </template><p v-else class="small muted">Starts after step 2.</p></div></li>
    </ol>
  </div>
</template>
<style scoped>
.steps { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 14px; }
.step { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 18px 20px; display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 14px; }
.step.todo { opacity: 0.6; }
.n { width: 28px; height: 28px; border-radius: 50%; background: var(--c-primary); color: #fff; font-weight: 700; font-size: 14px; display: grid; place-items: center; }
.step.done .n { background: var(--c-ok); } .step.todo .n { background: var(--c-fill-2); color: var(--c-text-3); }
.body { min-width: 0; } h2 { font-size: var(--fs-lg); margin: 2px 0 8px; }
</style>
