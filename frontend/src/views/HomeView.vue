<script setup>
// Overview, laid out like an instrument panel: a status card that says whether you need to act, then one card per
// thing you watch (the AI, fixes, services, hosts, the fleet), each with the same anatomy - name, what it is, a
// status line, one big measure and one bar. Below: the queue of incidents and the few switches that matter.
import { computed, ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import { rollup, speedVitals } from "@/lib/insight";
import { INCIDENT_KIND } from "@/lib/vocab";
import { useAppStore } from "@/stores/app";
import { useIncidentStore } from "@/stores/incidents";
import { useUiStore } from "@/stores/ui";
import { useI18n } from "@/lib/i18n";
import SeverityPill from "@/components/domain/SeverityPill.vue";

const app = useAppStore();
const incidents = useIncidentStore();
const ui = useUiStore();
const { t } = useI18n();
usePolling(() => incidents.loadList(), 15000);

const fleet = ref(null);
usePolling(async () => {
  try {
    const [g, clouds] = await Promise.all([api.network.graph(), api.cloud.accounts().catch(() => [])]);
    const machines = g.nodes.filter((n) => n.id.startsWith("host:") || n.id.startsWith("ip:") || n.kind === "cloud instance");
    fleet.value = { total: machines.length, monitored: machines.filter((n) => n.id.startsWith("host:")).length,
      networks: g.nodes.filter((n) => n.kind === "hub").length, clouds };
  } catch { fleet.value = null; }
}, 30000);

const settings = ref(null);
api.settings.get().then((r) => (settings.value = { ...r.settings })).catch(() => {});
async function saveSetting(key, value) {
  settings.value = { ...settings.value, [key]: value };
  try { await api.settings.update({ [key]: value }); ui.toast(t("Saved", "บันทึกแล้ว")); } catch (e) { ui.toast(e.message); }
}

const awaitingList = computed(() => app.awaiting);
const investigatingList = computed(() => app.openProblems.filter((p) => p.status !== "awaiting_approval"));
const queue = computed(() => [...awaitingList.value, ...investigatingList.value]);
const svc = computed(() => rollup(app.services));
const hst = computed(() => rollup(app.hosts));
const speed = computed(() => speedVitals(app.kpi));

const greeting = computed(() => {
  const h = new Date().getHours();
  return h < 12 ? t("Good morning", "อรุณสวัสดิ์") : h < 18 ? t("Good afternoon", "สวัสดีตอนบ่าย") : t("Good evening", "สวัสดีตอนเย็น");
});
const headline = computed(() => {
  const n = awaitingList.value.length, m = investigatingList.value.length;
  if (n) return { tone: "action", text: n > 1 ? t(`${n} fixes to approve`, `${n} วิธีแก้รออนุมัติ`) : t("A fix to approve", "มีวิธีแก้รออนุมัติ") };
  if (m) return { tone: "info", text: t("AI is investigating", "AI กำลังสืบสวน") };
  return { tone: "ok", text: t("All clear", "ทุกอย่างปกติ") };
});
const checks = computed(() => [
  { tone: awaitingList.value.length ? "warn" : investigatingList.value.length ? "info" : "ok", k: t("Incidents", "เหตุการณ์"),
    v: queue.value.length ? t(`${queue.value.length} open`, `เปิดอยู่ ${queue.value.length}`) : t("None open", "ไม่มีที่เปิดอยู่") },
  { tone: svc.value.affected ? "bad" : "ok", k: t("Services", "บริการ"),
    v: svc.value.affected ? t(`${svc.value.affected} of ${svc.value.total} with problems`, `มีปัญหา ${svc.value.affected} จาก ${svc.value.total}`) : t(`All ${svc.value.total} healthy`, `ปกติทั้ง ${svc.value.total}`) },
  { tone: hst.value.affected ? "bad" : "ok", k: t("Hosts", "เครื่อง"),
    v: hst.value.affected ? t(`${hst.value.affected} to check`, `ต้องดู ${hst.value.affected}`) : t(`All ${hst.value.total} reporting`, `รายงานครบ ${hst.value.total}`) },
  { tone: app.detectorLive ? "ok" : "neutral", k: t("Detector", "ตัวตรวจจับ"),
    v: app.detectorLive ? t(`Checked ${ago(app.overview?.detector?.ts)}`, `ตรวจเมื่อ ${ago(app.overview?.detector?.ts)}`) : t("Starting", "กำลังเริ่ม") },
]);
const primary = computed(() => {
  if (awaitingList.value.length) return { to: `/problems/${awaitingList.value[0].id}`, label: t("Review the fix", "ดูวิธีแก้") };
  if (queue.value.length) return { to: `/problems/${queue.value[0].id}`, label: t("Open incident", "เปิดเหตุการณ์") };
  return { to: "/network", label: t("Fleet", "ฟลีต") };
});

const resolvedShare = computed(() => (app.kpi.total ? (app.kpi.total - (app.kpi.open || 0)) / app.kpi.total : 0));
const avgCpu = computed(() => {
  const v = app.hosts.map((h) => h.cpu).filter((x) => x != null);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
});
const mmss = (s) => (s == null ? "–" : s < 60 ? `${Math.round(s)}s` : `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`);
const tone = (s, good, bad) => (s == null ? "neutral" : s <= good ? "ok" : s <= bad ? "warn" : "bad");

// incidents per day for the last 14 days: the one trend line on the page
const trend = computed(() => {
  const days = 14, now = Date.now() / 1000, bins = Array(days).fill(0);
  for (const i of incidents.list) {
    const d = Math.floor((now - i.detected_at) / 86400);
    if (d >= 0 && d < days) bins[days - 1 - d] += 1;
  }
  const max = Math.max(1, ...bins), W = 460, H = 92;
  const pts = bins.map((v, i) => [(i / (days - 1)) * W, H - 6 - (v / max) * (H - 18)]);
  const line = pts.map((p) => p.map((n) => n.toFixed(1)).join(",")).join(" ");
  return { line, area: `0,${H} ${line} ${W},${H}`, W, H, total: bins.reduce((a, b) => a + b, 0), today: bins[days - 1] };
});

const kindLabel = (i) => INCIDENT_KIND[i.kind]?.label || i.title;
const entityOf = (i) => i.entity_name || i.entity;
const SENS = computed(() => [{ value: "low", label: t("Fewer alerts", "แจ้งน้อย") }, { value: "normal", label: t("Normal", "ปกติ") },
  { value: "high", label: t("Catch more", "จับมากขึ้น") }]);
</script>
<template>
  <div class="page page--wide">
    <template v-if="app.overview">
      <UiPageHeader :eyebrow="greeting" :title="t('Overview', 'ภาพรวม')" />

      <div class="board">
        <!-- status: do I need to act? -->
        <section :class="['card', 'welcome', `t-${headline.tone}`]">
          <p class="welcome__k">{{ t("Right now", "ตอนนี้") }}</p>
          <h2 class="welcome__h">{{ headline.text }}</h2>
          <ul class="checks">
            <li v-for="c in checks" :key="c.k"><UiStatusDot :tone="c.tone" :size="10" /><div><b>{{ c.k }}</b><span>{{ c.v }}</span></div></li>
          </ul>
          <UiButton class="welcome__go" :variant="headline.tone === 'ok' ? 'tint' : 'primary'" :to="primary.to" chevron>{{ primary.label }}</UiButton>
        </section>

        <!-- the AI -->
        <section class="card metric">
          <div class="metric__top">
            <div>
              <h3>{{ t("AI investigation", "AI สืบสวน") }}</h3>
              <p class="sub">{{ t("Average time to a root cause", "เวลาเฉลี่ยจนได้สาเหตุ") }} · {{ app.llm.active || app.llm.models?.[0] || t("local model", "โมเดลในเครื่อง") }}</p>
              <p class="state"><UiStatusDot :tone="app.llm.up ? 'ok' : 'bad'" :size="9" />{{ app.llm.up ? t("Online", "พร้อม") : t("Offline", "ออฟไลน์") }}</p>
            </div>
            <UiGauge :size="104" :ratio="(speed[0].seconds || 0) / 300" :value="mmss(speed[0].seconds)" :unit="t('min', 'นาที')" :tone="tone(speed[0].seconds, 120, 300)" />
          </div>
          <UiBar :label="t('Incidents resolved', 'แก้ไขแล้ว')" :value="`${Math.round(resolvedShare * 100)}%`" :ratio="resolvedShare" />
          <router-link to="/problems" class="rail" :aria-label="t('Open incidents', 'เปิดเหตุการณ์')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- services -->
        <section class="card mini">
          <h3>{{ t("Services", "บริการ") }}</h3>
          <p class="sub">{{ t(`${app.services.length} watched`, `เฝ้าดู ${app.services.length}`) }}</p>
          <p class="state"><UiStatusDot :tone="svc.affected ? 'bad' : 'ok'" :size="9" />{{ svc.affected ? t(`${svc.affected} need a look`, `มีปัญหา ${svc.affected}`) : t("Healthy", "ปกติ") }}</p>
          <UiBar :label="t('Healthy', 'ปกติ')" :value="`${svc.total ? Math.round(((svc.total - svc.affected) / svc.total) * 100) : 0}%`"
                 :ratio="svc.total ? (svc.total - svc.affected) / svc.total : 0" />
          <router-link to="/services" class="rail" :aria-label="t('Open services', 'เปิดบริการ')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- hosts -->
        <section class="card mini">
          <h3>{{ t("Hosts", "เครื่อง") }}</h3>
          <p class="sub">{{ t(`${app.hosts.length} with our agent`, `มี agent ${app.hosts.length}`) }}</p>
          <p class="state"><UiStatusDot :tone="hst.affected ? 'bad' : 'ok'" :size="9" />{{ hst.affected ? t(`${hst.affected} to check`, `ต้องดู ${hst.affected}`) : t("Reporting", "รายงานปกติ") }}</p>
          <UiBar :label="t('CPU', 'CPU')" :value="avgCpu == null ? '–' : `${Math.round(avgCpu)}%`" :ratio="(avgCpu || 0) / 100"
                 :tone="avgCpu >= 90 ? 'bad' : avgCpu >= 70 ? 'warn' : undefined" />
          <router-link to="/network/list" class="rail" :aria-label="t('Open hosts', 'เปิดรายการเครื่อง')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- fixes -->
        <section class="card metric">
          <div class="metric__top">
            <div>
              <h3>{{ t("Fix after approval", "แก้หลังอนุมัติ") }}</h3>
              <p class="sub">{{ t("Average from approve to verified · dry run first", "เวลาเฉลี่ยจากอนุมัติถึงยืนยัน · dry run ก่อน") }}</p>
              <p class="state"><UiStatusDot :tone="awaitingList.length ? 'warn' : 'ok'" :size="9" />{{ awaitingList.length ? t(`${awaitingList.length} waiting for you`, `รอคุณ ${awaitingList.length}`) : t("Nothing waiting", "ไม่มีรายการรอ") }}</p>
            </div>
            <UiGauge :size="104" :ratio="(speed[1].seconds || 0) / 300" :value="mmss(speed[1].seconds)" :unit="t('min', 'นาที')" :tone="tone(speed[1].seconds, 120, 300)" />
          </div>
          <UiBar :label="t('Waiting for approval', 'รออนุมัติ')" :value="awaitingList.length" :ratio="queue.length ? awaitingList.length / queue.length : 0" tone="info" />
          <router-link to="/runbooks" class="rail" :aria-label="t('Open runbooks', 'เปิดคู่มือแก้ไข')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- fleet + the trend line -->
        <section class="card fleet">
          <div class="fleet__top">
            <div>
              <h3>{{ t("Fleet", "ฟลีต") }}</h3>
              <p class="sub">{{ fleet ? t(`${fleet.total} machines · ${fleet.networks} networks · ${fleet.clouds.length} cloud account${fleet.clouds.length === 1 ? "" : "s"}`, `${fleet.total} เครื่อง · ${fleet.networks} เครือข่าย · ${fleet.clouds.length} บัญชีคลาวด์`) : t("Loading", "กำลังโหลด") }}</p>
              <p class="state"><UiStatusDot :tone="fleet && fleet.monitored ? 'ok' : 'neutral'" :size="9" />{{ fleet ? t(`${fleet.monitored} monitored`, `เฝ้าดู ${fleet.monitored}`) : "–" }}</p>
            </div>
            <div class="fleet__nums"><span><b>{{ trend.today }}</b> {{ t("today", "วันนี้") }}</span><span><b>{{ trend.total }}</b> {{ t("in 14 days", "ใน 14 วัน") }}</span></div>
          </div>
          <svg :viewBox="`0 0 ${trend.W} ${trend.H}`" preserveAspectRatio="none" class="spark" role="img" :aria-label="t('Incidents per day, last 14 days', 'จำนวนเหตุการณ์ต่อวัน 14 วัน')">
            <polygon :points="trend.area" class="spark__a" /><polyline :points="trend.line" class="spark__l" vector-effect="non-scaling-stroke" />
          </svg>
          <p class="spark__cap">{{ t("Incidents per day", "เหตุการณ์ต่อวัน") }}</p>
          <router-link to="/network" class="rail" :aria-label="t('Open the Fleet', 'เปิดฟลีต')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- the queue -->
        <section class="card queue">
          <div class="queue__h"><h3>{{ t("Incident queue", "คิวเหตุการณ์") }}</h3><router-link to="/problems" class="link">{{ t("All incidents", "ทั้งหมด") }}</router-link></div>
          <div v-if="queue.length" class="rows">
            <div v-for="i in queue.slice(0, 5)" :key="i.id" class="row-i" @click="$router.push(`/problems/${i.id}`)">
              <UiStatusDot :tone="i.status === 'awaiting_approval' ? 'warn' : 'info'" :size="9" />
              <div class="row-i__b">
                <div class="row-i__t"><b>{{ kindLabel(i) }}</b> <span class="muted">{{ t("on", "ที่") }} {{ entityOf(i) }}</span></div>
                <div class="row-i__s">P-{{ i.id }} · {{ ago(i.detected_at) }}<template v-if="i.root_cause"> · {{ i.root_cause }}</template></div>
              </div>
              <SeverityPill :severity="i.severity" />
              <UiButton :variant="i.status === 'awaiting_approval' ? 'primary' : 'tint'" size="sm" :to="`/problems/${i.id}`" chevron @click.stop>
                {{ i.status === "awaiting_approval" ? t("Review", "ดู") : t("Open", "เปิด") }}</UiButton>
            </div>
          </div>
          <div v-else class="clear"><UiStatusDot tone="ok" :size="10" /><span>{{ t("Nothing needs you. The AI opens an incident the moment something drifts.", "ไม่มีอะไรต้องทำ AI จะเปิดเหตุการณ์ทันทีที่มีอะไรผิดปกติ") }}</span></div>
        </section>

        <!-- the switches that matter -->
        <section class="card prefs">
          <h3>{{ t("Platform settings", "ตั้งค่าแพลตฟอร์ม") }}</h3>
          <template v-if="settings">
            <p class="prefs__sec">{{ t("Investigation", "การสืบสวน") }}</p>
            <div class="pref"><span>{{ t("Investigate new incidents automatically", "สืบสวนเหตุการณ์ใหม่อัตโนมัติ") }}</span>
              <UiSwitch :model-value="settings.auto_analyze === '1'" :label="t('Investigate automatically', 'สืบสวนอัตโนมัติ')" @update:model-value="(v) => saveSetting('auto_analyze', v ? '1' : '0')" /></div>
            <p class="prefs__sec">{{ t("Detection", "การตรวจจับ") }}</p>
            <UiSegmented :model-value="settings.sensitivity || 'normal'" :options="SENS" :label="t('Sensitivity', 'ความไว')" @update:model-value="(v) => saveSetting('sensitivity', v)" />
            <div class="pref"><span>{{ t("Teams alerts", "แจ้งเตือน Teams") }}</span><span class="muted">{{ settings.teams_webhook ? t("On", "เปิด") : t("Not set", "ยังไม่ตั้ง") }}</span></div>
          </template>
          <UiButton variant="tint" block to="/settings" chevron class="prefs__all">{{ t("All settings", "การตั้งค่าทั้งหมด") }}</UiButton>
        </section>
      </div>
    </template>
    <UiWait v-else :title="t('Loading the overview', 'กำลังโหลดภาพรวม')" />
  </div>
</template>
<style scoped>
.board { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }
.card { position: relative; background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 22px 24px; min-width: 0; }
.card h3 { font-size: 22px; font-weight: var(--fw-semibold); letter-spacing: -0.02em; line-height: 1.2; }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 4px; }
.state { display: flex; align-items: center; gap: 8px; margin-top: 12px; font-weight: var(--fw-semibold); }
.muted { color: var(--c-text-2); }
/* the right-edge chevron rail every resource card carries */
.rail { position: absolute; top: 0; right: 0; bottom: 0; width: 44px; display: grid; place-items: center; color: var(--c-text-3);
  border-left: 1px solid var(--c-separator); border-radius: 0 var(--radius-lg) var(--radius-lg) 0; }
.rail:hover { background: var(--c-hover); color: var(--c-text); }
.metric, .mini, .fleet { padding-right: 64px; display: flex; flex-direction: column; justify-content: space-between; gap: 22px; }
.mini { padding: 22px 50px 22px 22px; } .mini .rail { width: 34px; }
.mini .state { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; }

.welcome { grid-column: span 4; grid-row: span 2; display: flex; flex-direction: column; }
.welcome__k { color: var(--c-text-3); }
.welcome__h { font-size: var(--fs-hero); font-weight: var(--fw-bold); letter-spacing: -0.035em; line-height: 1.02; margin-top: 4px; }
.t-action .welcome__h { color: var(--c-warn-text); }
.checks { list-style: none; padding: 0; margin: auto 0 0; display: flex; flex-direction: column; gap: 14px; padding-top: 28px; }
.checks li { display: flex; gap: 12px; align-items: flex-start; } .checks li .ui-dot { margin-top: 5px; }
.checks b { display: block; font-weight: var(--fw-semibold); } .checks span { font-size: var(--fs-sm); color: var(--c-text-3); }
.welcome__go { align-self: flex-end; margin-top: 22px; }

.metric { grid-column: span 4; }
.metric__top { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.mini { grid-column: span 2; }
.fleet { grid-column: span 4; gap: 10px; }
.fleet__top { display: flex; justify-content: space-between; gap: 12px; }
.fleet__nums { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; font-size: var(--fs-sm); color: var(--c-text-3); white-space: nowrap; }
.fleet__nums b { color: var(--c-text); font-size: var(--fs-md); }
.spark { width: 100%; height: 92px; display: block; margin-top: 6px; }
.spark__a { fill: var(--c-primary); opacity: 0.14; } .spark__l { fill: none; stroke: var(--c-primary); stroke-width: 2; stroke-linejoin: round; }
.spark__cap { font-size: var(--fs-xs); color: var(--c-text-3); }

.queue { grid-column: span 8; }
.queue__h { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
.link { font-size: var(--fs-sm); font-weight: var(--fw-semibold); }
.rows { display: flex; flex-direction: column; }
.row-i { display: flex; align-items: center; gap: 14px; padding: 14px 4px; border-top: 1px solid var(--c-separator); cursor: pointer; }
.row-i:first-child { border-top: 0; }
.row-i:hover .row-i__t b { color: var(--c-primary); }
.row-i__b { flex: 1; min-width: 0; }
.row-i__s { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.clear { display: flex; align-items: center; gap: 12px; padding: 22px 4px; color: var(--c-text-2); }

.prefs { grid-column: span 4; display: flex; flex-direction: column; gap: 14px; }
.prefs__sec { font-size: 10.5px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.09em; color: var(--c-text-3); margin-top: 6px; }
.pref { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.prefs__all { margin-top: auto; }

@media (max-width: 1280px) {
  .welcome { grid-column: span 6; grid-row: span 1; } .metric { grid-column: span 6; } .mini { grid-column: span 3; } .fleet { grid-column: span 6; }
  .queue { grid-column: span 12; } .prefs { grid-column: span 12; }
}
@media (max-width: 760px) {
  .board { grid-template-columns: 1fr; }
  .welcome, .metric, .mini, .fleet, .queue, .prefs { grid-column: auto; }
  .welcome__h { font-size: 36px; } .row-i__s { white-space: normal; }
}
</style>
