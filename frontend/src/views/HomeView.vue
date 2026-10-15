<script setup>
// Overview answers three questions, top to bottom:
//   1. Is everything OK?               -> one status line (orange when a person is needed)
//   2. Does anything need me?          -> the incident queue, each with its lifecycle
//   3. How is each system doing?       -> services and hosts as tables, with 7 days of incident history
import { computed, ref } from "vue";
import HistoryStrip from "@/components/domain/HistoryStrip.vue";
import IncidentCard from "@/components/domain/IncidentCard.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago, dur, ms, num, pct, rate } from "@/lib/format";
import { rollup } from "@/lib/insight";
import { HEALTH_TONE, kindIcon, languageLogo, osLogo } from "@/lib/vocab";
import { useAppStore } from "@/stores/app";
import { useIncidentStore } from "@/stores/incidents";

const app = useAppStore();
const incidents = useIncidentStore();
usePolling(() => incidents.loadList(), 15000);

// Fleet coverage: one clear next action — how much of the fleet AIOps watches, and what to connect next.
const coverage = ref(null);
usePolling(async () => {
  try {
    const [recs, disc] = await Promise.all([api.network.recommendations(), api.network.discovered()]);
    const monitored = app.hosts.length;
    coverage.value = { monitored, total: Math.max(disc.summary.machines, monitored), suggest: recs.count, top: recs.recommendations[0] };
  } catch { coverage.value = null; }
}, 30000);

const queue = computed(() => [...app.awaiting, ...app.openProblems.filter((p) => p.status !== "awaiting_approval")]);
const lastResolved = computed(() => incidents.list.find((i) => i.status === "resolved"));
const status = computed(() => {
  const n = app.awaiting.length, m = queue.value.length - n;
  if (n) return { tone: "action", title: n > 1 ? `${n} fixes are waiting for your approval` : "A fix is waiting for your approval",
    sub: "The AI has found the cause and tested each fix in a dry run. Nothing changes until you approve." };
  if (m) return { tone: "info", title: m > 1 ? `The AI is investigating ${m} incidents` : "The AI is investigating an incident",
    sub: "You will be asked to approve a fix as soon as one is ready." };
  return { tone: "ok", title: "Everything is working normally",
    sub: lastResolved.value ? `The last incident was resolved ${ago(lastResolved.value.resolved_at || lastResolved.value.detected_at)}.` : "No incidents so far." };
});
// "affected out of total", worst state first (Dynatrace / Carbon pattern); silence is counted, not hidden
const health = computed(() => [
  { label: "Services", ...rollup(app.services), to: "/services" },
  { label: "Hosts", ...rollup(app.hosts), to: "/network" },
]);
const historyFor = (name) => incidents.list.filter((i) => (i.entity_name || i.entity) === name);
const healthLabel = { healthy: "Healthy", problem: "Problem", down: "Down", offline: "Offline", "no-data": "No data" };

// How the platform handles an incident, with the real averages from this installation
const FLOW = computed(() => [
  { title: "Detect", value: dur(app.kpi.mttd_s), hint: "from the first bad signal" },
  { title: "Investigate", value: "AI", hint: "reads metrics, traces and logs" },
  { title: "Approve", value: "You", hint: "nothing changes without you", you: true },
  { title: "Fix and verify", value: dur(app.kpi.mttr_s), hint: "from detection to verified" },
]);
</script>
<template>
  <div class="page">
    <template v-if="app.overview">
      <section :class="['status', `status--${status.tone}`]" aria-live="polite">
        <span class="status__mark" aria-hidden="true">
          <UiIcon :name="status.tone === 'ok' ? 'checkmark' : status.tone === 'action' ? 'person' : 'sparkle'" :size="20" />
        </span>
        <div class="status__text">
          <h1>{{ status.title }}</h1>
          <p>{{ status.sub }}</p>
          <ul class="roll" aria-label="Health summary">
            <li v-for="h in health" :key="h.label"><router-link :to="h.to">
              <UiStatusDot :tone="h.affected ? 'bad' : 'ok'" :size="8" />
              <b>{{ h.affected }} of {{ h.total }}</b> {{ h.label.toLowerCase() }} affected<span v-if="h.quiet" class="dim"> · {{ h.quiet }} sending no data</span>
            </router-link></li>
          </ul>
        </div>
        <span class="status__checked">Checked {{ ago(app.overview.detector?.ts) }}</span>
      </section>

      <ol class="flow" aria-label="How an incident is handled">
        <li v-for="f in FLOW" :key="f.title" :class="{ you: f.you }">
          <span class="flow__t">{{ f.title }}</span>
          <b class="flow__v">{{ f.value }}</b>
          <span class="flow__h">{{ f.hint }}</span>
        </li>
      </ol>

      <router-link v-if="coverage && coverage.suggest" to="/network" class="coverage">
        <div class="coverage__text">
          <b>Monitoring {{ coverage.monitored }} of {{ coverage.total }} machines</b>
          <span>{{ coverage.suggest }} more worth connecting<template v-if="coverage.top">, starting with {{ coverage.top.name }} — {{ coverage.top.reasons[0] }}</template>.</span>
        </div>
        <span class="coverage__cta">Review on the Fleet<UiIcon name="chevron_right" :size="16" /></span>
      </router-link>

      <section v-if="queue.length">
        <h2 class="section-title">Open incidents <router-link to="/problems">All incidents</router-link></h2>
        <div class="queue"><IncidentCard v-for="p in queue" :key="p.id" :incident="p" /></div>
      </section>

      <section>
        <h2 class="section-title">Services <router-link to="/map">Service map</router-link></h2>
        <div class="table-wrap">
          <table class="tbl">
            <thead><tr><th>Service</th><th>Status</th><th class="r">Requests</th><th class="r">Errors</th><th class="r">p95</th><th>Last 7 days</th></tr></thead>
            <tbody>
              <tr v-for="s in app.services" :key="s.service" @click="$router.push(`/services/${s.service}`)">
                <td><div class="who"><UiAppTile :logo="languageLogo(s.language || s.service)" :icon="kindIcon(s.kind)" :size="24" />
                  <router-link :to="`/services/${s.service}`" @click.stop>{{ s.name }}</router-link><span v-if="s.version" class="ver">v{{ s.version }}</span></div></td>
                <td><span class="health"><UiStatusDot :tone="HEALTH_TONE[s.status]" :size="7" />{{ healthLabel[s.status] || s.status }}</span></td>
                <td class="r num">{{ rate(s.rps) }}</td>
                <td :class="['r', 'num', { bad: s.error_rate > 0.05 }]">{{ pct(s.error_rate) }}</td>
                <td class="r num">{{ ms(s.p95_ms) }}</td>
                <td><HistoryStrip :incidents="historyFor(s.service)" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div class="cols">
        <section>
          <h2 class="section-title">Hosts <router-link to="/computers">All hosts</router-link></h2>
          <div class="table-wrap">
            <table class="tbl">
              <thead><tr><th>Host</th><th>CPU</th><th>Memory</th><th>Disk</th><th>Last 7 days</th></tr></thead>
              <tbody>
                <tr v-for="h in app.hosts" :key="h.name" @click="$router.push(`/computers/${h.name}`)">
                  <td><div class="who"><UiAppTile :logo="osLogo(h.os)" :icon="h.kind === 'workstation' ? 'laptop' : 'server'" :status="HEALTH_TONE[h.status]" :size="24" />
                    <router-link :to="`/computers/${h.name}`" @click.stop>{{ h.name }}</router-link></div></td>
                  <td v-for="m in ['cpu', 'mem', 'disk']" :key="m" class="num">
                    <span :class="['use', { warn: h[m] >= 70, bad: h[m] >= 90 }]"><i><b :style="{ width: `${Math.min(h[m] || 0, 100)}%` }" /></i>{{ h[m] == null ? "-" : `${Math.round(h[m])}%` }}</span>
                  </td>
                  <td><HistoryStrip :incidents="historyFor(h.name)" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section v-if="app.discovered.length">
          <h2 class="section-title">Found running on your hosts</h2>
          <UiList>
            <UiListRow v-for="s in app.discovered.slice(0, 5)" :key="s.service" :to="`/services/${s.service}`" :title="s.name"
                       :subtitle="`On ${s.hosts.join(', ')}, seen ${ago(s.last_seen)}`">
              <template #leading><UiAppTile :logo="languageLogo(s.language || s.service)" :icon="kindIcon(s.kind)" :size="24" /></template>
            </UiListRow>
          </UiList>
        </section>
      </div>
    </template>
    <UiWait v-else title="Loading the overview" />
  </div>
</template>
<style scoped>
.status { display: flex; align-items: center; gap: 14px; padding: 24px 0 18px; }
.status__mark { width: 36px; height: 36px; border-radius: var(--radius-md); display: grid; place-items: center; flex: none; color: #fff; }
.status--ok .status__mark { background: var(--c-ok); }
.status--info .status__mark { background: var(--c-primary); position: relative; }
/* AI at work: a soft blue ring breathing out of the mark */
.status--info .status__mark::after { content: ""; position: absolute; inset: 0; border-radius: inherit;
  box-shadow: 0 0 0 0 var(--c-halo); animation: think 2s var(--ease, ease-out) infinite; }
@keyframes think { 0% { box-shadow: 0 0 0 0 var(--c-halo); } 70%, 100% { box-shadow: 0 0 0 10px transparent; } }
.status--info .status__mark .ui-icon { animation: think-spin 3s var(--ease, ease-in-out) infinite; transform-origin: center; }
@keyframes think-spin { 0%, 100% { transform: rotate(0); } 50% { transform: rotate(8deg); } }
.status--action .status__mark { background: var(--c-action); color: var(--c-on-action); }
@media (prefers-reduced-motion: reduce) { .status--info .status__mark::after, .status--info .status__mark .ui-icon { animation: none; } }
.status__text { flex: 1; min-width: 0; }
.status h1 { font-size: var(--fs-3xl); line-height: 1.2; font-weight: var(--fw-semibold); }
.status p { color: var(--c-text-2); margin-top: 4px; }
.roll { list-style: none; display: flex; flex-wrap: wrap; gap: 6px 18px; margin: 10px 0 0; padding: 0; font-size: var(--fs-sm); }
.roll a { display: inline-flex; align-items: center; gap: 6px; color: var(--c-text-2); text-decoration: none; }
.roll a:hover { color: var(--c-text); } .roll b { color: var(--c-text); font-variant-numeric: tabular-nums; }
.status__checked { font-size: var(--fs-sm); color: var(--c-text-3); white-space: nowrap; align-self: flex-start; padding-top: 8px; }

.flow { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); list-style: none; margin: 0; padding: 0;
  border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow: hidden; background: var(--c-surface); }
.flow li { position: relative; padding: 12px 16px 12px 18px; display: flex; flex-direction: column; min-width: 0; }
.flow li + li { border-left: 1px solid var(--c-border); }
.flow li + li::before { content: ""; position: absolute; left: -6px; top: 50%; width: 10px; height: 10px; transform: translateY(-50%) rotate(45deg);
  background: var(--c-surface); border-top: 1px solid var(--c-border); border-right: 1px solid var(--c-border); }
.flow__t { font-size: var(--fs-sm); color: var(--c-text-2); }
.flow__v { font-size: var(--fs-xl); font-weight: var(--fw-semibold); font-variant-numeric: tabular-nums; color: var(--c-primary); }
.flow li.you .flow__v { color: var(--c-action-text); }
.flow__h { font-size: var(--fs-xs); color: var(--c-text-3); }

.coverage { display: flex; align-items: center; gap: 16px; margin-top: 14px; padding: 14px 18px; background: var(--c-surface);
  border: 1px solid var(--c-border); border-radius: var(--radius-lg); color: var(--c-text); text-decoration: none; }
.coverage:hover { border-color: var(--c-primary); }
.coverage__text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.coverage__text b { font-size: var(--fs-md); font-variant-numeric: tabular-nums; }
.coverage__text span { color: var(--c-text-2); font-size: var(--fs-sm); }
.coverage__cta { display: inline-flex; align-items: center; gap: 2px; color: var(--c-primary); font-weight: var(--fw-semibold); font-size: var(--fs-sm); white-space: nowrap; }

.queue { display: flex; flex-direction: column; gap: 10px; }

.table-wrap { border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow-x: auto; background: var(--c-surface); }
.tbl { width: 100%; border-collapse: collapse; font-size: var(--fs-md); }
.tbl th { text-align: left; font-size: var(--fs-xs); font-weight: var(--fw-medium); color: var(--c-text-3); padding: 8px 14px; background: var(--c-raised);
  border-bottom: 1px solid var(--c-border); white-space: nowrap; }
.tbl td { padding: 9px 14px; border-top: 1px solid var(--c-separator); white-space: nowrap; }
.tbl tbody tr:first-child td { border-top: 0; }
.tbl tbody tr { cursor: pointer; }
.tbl tbody tr:hover td { background: var(--c-hover); }
.tbl .r { text-align: right; }
.tbl .bad { color: var(--c-bad-text); font-weight: var(--fw-semibold); }
.who { display: flex; align-items: center; gap: 10px; }
.who a { color: var(--c-text); font-weight: var(--fw-medium); }
.ver { font-family: var(--font-mono); font-size: var(--fs-xs); color: var(--c-text-3); }
.health { display: inline-flex; align-items: center; gap: 7px; color: var(--c-text-2); }
.use { display: inline-flex; align-items: center; gap: 8px; min-width: 84px; color: var(--c-text-2); }
.use i { display: block; width: 40px; height: 4px; border-radius: 2px; background: var(--c-fill-2); overflow: hidden; }
.use b { display: block; height: 100%; background: var(--bar); }
.use { --bar: var(--c-ok); }
.use.warn { --bar: var(--c-warn); } .use.bad { --bar: var(--c-bad); color: var(--c-bad-text); }
.cols { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 24px; align-items: start; }
@media (max-width: 1080px) { .cols { grid-template-columns: 1fr; } .flow { grid-template-columns: repeat(2, minmax(0, 1fr)); } .flow li:nth-child(3) { border-left: 0; } .flow li:nth-child(n + 3) { border-top: 1px solid var(--c-border); } .flow li:nth-child(3)::before { display: none; } }
@media (max-width: 760px) { .status h1 { font-size: 22px; } .status__checked { display: none; } }
</style>
