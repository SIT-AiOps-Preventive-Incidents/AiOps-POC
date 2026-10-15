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
import { useI18n } from "@/lib/i18n";

const app = useAppStore();
const incidents = useIncidentStore();
const { t, locale } = useI18n();
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
  if (n) return { tone: "action", title: n > 1 ? t(`${n} fixes are waiting for your approval`, `มี ${n} การแก้ไขรอคุณอนุมัติ`) : t("A fix is waiting for your approval", "มีการแก้ไขรอคุณอนุมัติ"),
    sub: t("The AI has found the cause and tested each fix in a dry run. Nothing changes until you approve.", "AI หาสาเหตุเจอและทดสอบการแก้ไขแต่ละอันแบบ dry run แล้ว ไม่มีอะไรเปลี่ยนจนกว่าคุณจะอนุมัติ") };
  if (m) return { tone: "info", title: m > 1 ? t(`The AI is investigating ${m} incidents`, `AI กำลังสืบสวน ${m} เหตุการณ์`) : t("The AI is investigating an incident", "AI กำลังสืบสวนเหตุการณ์"),
    sub: t("You will be asked to approve a fix as soon as one is ready.", "เมื่อการแก้ไขพร้อม ระบบจะให้คุณอนุมัติ") };
  return { tone: "ok", title: t("Everything is working normally", "ทุกอย่างทำงานปกติ"),
    sub: lastResolved.value ? t(`The last incident was resolved ${ago(lastResolved.value.resolved_at || lastResolved.value.detected_at)}.`, `เหตุการณ์ล่าสุดแก้ไขเสร็จ ${ago(lastResolved.value.resolved_at || lastResolved.value.detected_at)}`) : t("No incidents so far.", "ยังไม่มีเหตุการณ์") };
});
const historyFor = (name) => incidents.list.filter((i) => (i.entity_name || i.entity) === name);
const healthLabel = computed(() => ({ healthy: t("Healthy", "ปกติ"), problem: t("Problem", "มีปัญหา"), down: t("Down", "ล่ม"), offline: t("Offline", "ออฟไลน์"), "no-data": t("No data", "ไม่มีข้อมูล") }));

// At-a-glance vital signs: what needs me, and how much is healthy
const kpis = computed(() => {
  const s = rollup(app.services), h = rollup(app.hosts);
  const inv = Math.max(queue.value.length - app.awaiting.length, 0);
  return [
    { label: t("Awaiting you", "รอคุณอนุมัติ"), value: app.awaiting.length, tone: app.awaiting.length ? "action" : "none", to: "/problems" },
    { label: t("Investigating", "กำลังสืบสวน"), value: inv, tone: inv ? "info" : "none", to: "/problems" },
    { label: t("Services healthy", "บริการปกติ"), value: `${s.total - s.affected}/${s.total}`, tone: s.affected ? "bad" : "ok", to: "/services" },
    { label: t("Hosts healthy", "เครื่องปกติ"), value: `${h.total - h.affected}/${h.total}`, tone: h.affected ? "bad" : "ok", to: "/network" },
    { label: t("Avg fix time", "เวลาแก้เฉลี่ย"), value: dur(app.kpi.mttr_s), tone: "none", to: "/problems" },
  ];
});
// problems and silence rise to the top of the tables; healthy settles below, alphabetically
const SRANK = { problem: 0, down: 0, error: 0, offline: 1, "no-data": 2, healthy: 3 };
const srank = (x) => SRANK[x] ?? 1;
const sortedServices = computed(() => [...app.services].sort((a, b) => srank(a.status) - srank(b.status) || (a.name || "").localeCompare(b.name || "")));
const sortedHosts = computed(() => [...app.hosts].sort((a, b) => srank(a.status) - srank(b.status) || (a.name || "").localeCompare(b.name || "")));

// the single most important next action, spelled out as the hero's button
const primary = computed(() => {
  if (app.awaiting.length) return { to: `/problems/${app.awaiting[0].id}`, label: t("Review the first fix", "ดูการแก้ไขแรก"), icon: "checkmark", variant: "action" };
  if (queue.value.length) return { to: `/problems/${queue.value[0].id}`, label: t("Open the incident", "เปิดเหตุการณ์"), icon: "chevron_right", variant: "primary" };
  return { to: "/network", label: t("Open the Fleet", "เปิดฟลีต"), icon: "server", variant: "tint" };
});
</script>
<template>
  <div class="page">
    <template v-if="app.overview">
      <section :class="['hero', `hero--${status.tone}`]" aria-live="polite">
        <span class="hero__mark" aria-hidden="true">
          <UiIcon :name="status.tone === 'ok' ? 'checkmark' : status.tone === 'action' ? 'person' : 'sparkle'" :size="22" />
        </span>
        <div class="hero__text">
          <h1>{{ status.title }}</h1>
          <p>{{ status.sub }}</p>
        </div>
        <div class="hero__side">
          <UiButton :variant="primary.variant" size="lg" :to="primary.to" :icon="primary.icon">{{ primary.label }}</UiButton>
          <span class="hero__checked">{{ t("Checked", "ตรวจเมื่อ") }} {{ ago(app.overview.detector?.ts) }}</span>
        </div>
      </section>

      <div class="kpis" aria-label="Vital signs">
        <router-link v-for="k in kpis" :key="k.label" :to="k.to" :class="['kpi', `kpi--${k.tone}`]">
          <b class="kpi__v">{{ k.value }}</b>
          <span class="kpi__l">{{ k.label }}</span>
        </router-link>
      </div>

      <router-link v-if="coverage && coverage.suggest" to="/network" class="coverage">
        <div class="coverage__text">
          <b>{{ t("Monitoring", "เฝ้าดู") }} {{ coverage.monitored }} {{ t("of", "จาก") }} {{ coverage.total }} {{ t("machines", "เครื่อง") }}</b>
          <span><template v-if="locale === 'th'">อีก {{ coverage.suggest }} เครื่องน่าเชื่อมต่อ<template v-if="coverage.top"> เริ่มจาก {{ coverage.top.name }} — {{ coverage.top.reasons[0] }}</template></template><template v-else>{{ coverage.suggest }} more worth connecting<template v-if="coverage.top">, starting with {{ coverage.top.name }} — {{ coverage.top.reasons[0] }}</template>.</template></span>
        </div>
        <span class="coverage__cta">{{ t("Review on the Fleet", "ดูในฟลีต") }}<UiIcon name="chevron_right" :size="16" /></span>
      </router-link>

      <section v-if="queue.length">
        <h2 class="section-title"><span class="st-l"><UiIcon name="warning" :size="16" />{{ t("Open incidents", "เหตุการณ์ที่เปิดอยู่") }}</span><router-link to="/problems">{{ t("All incidents", "เหตุการณ์ทั้งหมด") }}</router-link></h2>
        <div class="queue"><IncidentCard v-for="p in queue" :key="p.id" :incident="p" /></div>
      </section>

      <section>
        <h2 class="section-title"><span class="st-l"><UiIcon name="cube" :size="16" />{{ t("Services", "บริการ") }}</span><router-link to="/map">{{ t("Service map", "แผนผังบริการ") }}</router-link></h2>
        <div class="table-wrap">
          <table class="tbl">
            <thead><tr><th>{{ t("Service", "บริการ") }}</th><th>{{ t("Status", "สถานะ") }}</th><th class="r">{{ t("Requests", "คำขอ") }}</th><th class="r">{{ t("Errors", "ข้อผิดพลาด") }}</th><th class="r">p95</th><th>{{ t("Last 7 days", "7 วันล่าสุด") }}</th></tr></thead>
            <tbody>
              <tr v-for="s in sortedServices.slice(0, 8)" :key="s.service" @click="$router.push(`/services/${s.service}`)">
                <td><div class="who"><UiAppTile :logo="languageLogo(s.language || s.service)" :icon="kindIcon(s.kind)" :size="24" />
                  <router-link :to="`/services/${s.service}`" @click.stop>{{ s.name }}</router-link><span v-if="s.version" class="ver">v{{ s.version }}</span></div></td>
                <td><span class="health"><UiStatusDot :tone="HEALTH_TONE[s.status]" :size="7" />{{ healthLabel[s.status] || s.status }}</span></td>
                <td class="r num">{{ rate(s.rps) }}</td>
                <td :class="['r', 'num', { bad: s.error_rate > 0.05 }]">{{ pct(s.error_rate) }}</td>
                <td class="r num">{{ ms(s.p95_ms) }}</td>
                <td><HistoryStrip :incidents="historyFor(s.service)" /></td>
              </tr>
              <tr v-if="sortedServices.length > 8" class="more-row" @click="$router.push('/services')">
                <td colspan="6">{{ t(`View all ${sortedServices.length} services`, `ดูบริการทั้งหมด ${sortedServices.length} รายการ`) }} →</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div class="cols">
        <section>
          <h2 class="section-title"><span class="st-l"><UiIcon name="server" :size="16" />{{ t("Hosts", "เครื่อง") }}</span><router-link to="/computers">{{ t("All hosts", "เครื่องทั้งหมด") }}</router-link></h2>
          <div class="table-wrap">
            <table class="tbl">
              <thead><tr><th>{{ t("Host", "เครื่อง") }}</th><th>CPU</th><th>{{ t("Memory", "หน่วยความจำ") }}</th><th>{{ t("Disk", "ดิสก์") }}</th><th>{{ t("Last 7 days", "7 วันล่าสุด") }}</th></tr></thead>
              <tbody>
                <tr v-for="h in sortedHosts" :key="h.name" @click="$router.push(`/computers/${h.name}`)">
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
          <h2 class="section-title"><span class="st-l"><UiIcon name="search" :size="16" />{{ t("Found running on your hosts", "พบกำลังทำงานบนเครื่องของคุณ") }}</span></h2>
          <UiList>
            <UiListRow v-for="s in app.discovered.slice(0, 5)" :key="s.service" :to="`/services/${s.service}`" :title="s.name"
                       :subtitle="locale === 'th' ? `บน ${s.hosts.join(', ')} · เห็นล่าสุด ${ago(s.last_seen)}` : `On ${s.hosts.join(', ')}, seen ${ago(s.last_seen)}`">
              <template #leading><UiAppTile :logo="languageLogo(s.language || s.service)" :icon="kindIcon(s.kind)" :size="24" /></template>
            </UiListRow>
          </UiList>
        </section>
      </div>
    </template>
    <UiWait v-else :title="t('Loading the overview', 'กำลังโหลดภาพรวม')" />
  </div>
</template>
<style scoped>
/* Hero: the one focal banner. Colour by state, a left accent bar, and the single next action as a button on
   the right - so the eye lands here first and knows what to do. */
.hero { display: flex; align-items: center; gap: 16px; padding: 18px 22px 18px 24px; margin: 8px 0 16px; position: relative; overflow: hidden;
  border: 1px solid var(--c-border); border-radius: var(--radius-xl); background: var(--c-surface); }
.hero::before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--c-neutral); }
.hero--action { background: var(--c-action-bg); border-color: color-mix(in srgb, var(--c-action) 35%, var(--c-border)); }
.hero--action::before { background: var(--c-action); }
.hero--info { background: var(--c-primary-tint); border-color: color-mix(in srgb, var(--c-primary) 30%, var(--c-border)); }
.hero--info::before { background: var(--c-primary); }
.hero--ok { background: var(--c-ok-bg); border-color: color-mix(in srgb, var(--c-ok) 30%, var(--c-border)); }
.hero--ok::before { background: var(--c-ok); }
.hero__mark { width: 40px; height: 40px; border-radius: var(--radius-md); display: grid; place-items: center; flex: none; color: #fff; }
.hero--action .hero__mark { background: var(--c-action); color: var(--c-on-action); }
.hero--info .hero__mark { background: var(--c-primary); }
.hero--ok .hero__mark { background: var(--c-ok); }
.hero__text { flex: 1; min-width: 0; }
.hero__text h1 { font-size: var(--fs-2xl); line-height: 1.2; font-weight: var(--fw-semibold); }
.hero__text p { color: var(--c-text-2); margin-top: 3px; }
.hero__side { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; flex: none; }
.hero__checked { font-size: var(--fs-xs); color: var(--c-text-3); white-space: nowrap; }
@media (max-width: 760px) { .hero { flex-wrap: wrap; } .hero__text { flex-basis: 100%; } .hero__side { width: 100%; align-items: stretch; } }

/* vital-signs KPI tiles: the five numbers an on-call engineer scans first */
.kpis { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; }
.kpi { display: flex; flex-direction: column; gap: 3px; padding: 12px 16px; background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); text-decoration: none; color: var(--c-text); }
.kpi:hover { border-color: var(--c-primary); }
.kpi__v { font-size: var(--fs-2xl); font-weight: var(--fw-bold); font-variant-numeric: tabular-nums; line-height: 1.1; }
.kpi__l { font-size: var(--fs-sm); color: var(--c-text-2); }
.kpi--action { border-color: color-mix(in srgb, var(--c-action) 45%, var(--c-border)); }
.kpi--action .kpi__v { color: var(--c-action-text); } .kpi--info .kpi__v { color: var(--c-primary); }
.kpi--ok .kpi__v { color: var(--c-ok-text); } .kpi--bad .kpi__v { color: var(--c-bad-text); }
@media (max-width: 1080px) { .kpis { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 560px) { .kpis { grid-template-columns: repeat(2, 1fr); } }

.coverage { display: flex; align-items: center; gap: 16px; margin-top: 14px; padding: 14px 18px; background: var(--c-surface);
  border: 1px solid var(--c-border); border-radius: var(--radius-lg); color: var(--c-text); text-decoration: none; }
.coverage:hover { border-color: var(--c-primary); }
.coverage__text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.coverage__text b { font-size: var(--fs-md); font-variant-numeric: tabular-nums; }
.coverage__text span { color: var(--c-text-2); font-size: var(--fs-sm); }
.coverage__cta { display: inline-flex; align-items: center; gap: 2px; color: var(--c-primary); font-weight: var(--fw-semibold); font-size: var(--fs-sm); white-space: nowrap; }

.more-row td { text-align: center; color: var(--c-primary); font-weight: var(--fw-medium); font-size: var(--fs-sm); }
.more-row:hover td { background: var(--c-hover); }
.st-l { display: inline-flex; align-items: center; gap: 8px; }
.st-l .ui-icon { color: var(--c-text-3); }
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
@media (max-width: 1080px) { .cols { grid-template-columns: 1fr; } }
@media (max-width: 760px) { .hero__text h1 { font-size: 20px; } }
</style>
