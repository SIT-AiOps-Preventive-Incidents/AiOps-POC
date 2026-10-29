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
import StatusPill from "@/components/domain/StatusPill.vue";

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

// incidents over 14 days in 6-hour steps: the one trend line on the page, jagged like real traffic
const trend = computed(() => {
  const step = 6 * 3600, n = 56, now = Date.now() / 1000, bins = Array(n).fill(0);
  let opened = 0, resolved = 0;
  for (const i of incidents.list) {
    const k = Math.floor((now - i.detected_at) / step);
    if (k >= 0 && k < n) { bins[n - 1 - k] += 1; opened += 1; if (i.status === "resolved" || i.status === "closed") resolved += 1; }
  }
  const max = Math.max(1, ...bins), W = 480, H = 110;
  const pts = bins.map((v, i) => [(i / (n - 1)) * W, H - 4 - (v / max) * (H - 22)]);
  const line = pts.map((p) => p.map((x) => x.toFixed(1)).join(",")).join(" ");
  return { line, area: `0,${H} ${line} ${W},${H}`, W, H, opened, resolved };
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
          <UiDotArt variant="sphere" class="art art--orb" from="#5a46c8" via="#6f8ff0" to="#2fc98b" fade="left" :seed="2" />
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
              <p class="sub">{{ app.llm.active || app.llm.models?.[0] || t("local model", "โมเดลในเครื่อง") }} · {{ t("on CPU", "บน CPU") }}</p>
              <p class="state"><UiStatusDot :tone="app.llm.up ? 'ok' : 'bad'" :size="9" />{{ app.llm.up ? t("Online", "พร้อม") : t("Offline", "ออฟไลน์") }}</p>
            </div>
            <UiGauge :size="112" :ratio="(speed[0].seconds || 0) / 180" :value="mmss(speed[0].seconds)" :unit="t('to root cause', 'ถึงสาเหตุ')" tone="info" />
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
              <p class="sub">{{ t("Dry run first, then the owner decides", "dry run ก่อน แล้วเจ้าของตัดสินใจ") }}</p>
              <p class="state"><UiStatusDot :tone="awaitingList.length ? 'warn' : 'ok'" :size="9" />{{ awaitingList.length ? t(`${awaitingList.length} waiting for you`, `รอคุณ ${awaitingList.length}`) : t("Nothing waiting", "ไม่มีรายการรอ") }}</p>
            </div>
            <UiGauge :size="112" :ratio="(speed[1].seconds || 0) / 180" :value="mmss(speed[1].seconds)" :unit="t('to verified', 'ถึงยืนยัน')" tone="info" />
          </div>
          <UiBar :label="t('Waiting for approval', 'รออนุมัติ')" :value="awaitingList.length" :ratio="queue.length ? awaitingList.length / queue.length : 0" />
          <router-link to="/runbooks" class="rail" :aria-label="t('Open runbooks', 'เปิดคู่มือแก้ไข')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- fleet + the trend line -->
        <section class="card fleet">
          <div class="fleet__top">
            <div>
              <h3>{{ t("Fleet", "ฟลีต") }}</h3>
              <p class="sub">{{ fleet ? t(`${fleet.total} machines · ${fleet.clouds.length} cloud account${fleet.clouds.length === 1 ? "" : "s"}`, `${fleet.total} เครื่อง · ${fleet.clouds.length} บัญชีคลาวด์`) : t("Loading", "กำลังโหลด") }}</p>
              <p class="state"><UiStatusDot :tone="fleet && fleet.monitored ? 'ok' : 'neutral'" :size="9" />{{ fleet ? t(`${fleet.monitored} monitored`, `เฝ้าดู ${fleet.monitored}`) : "–" }}</p>
            </div>
            <div class="fleet__nums">
              <span :title="t('Incidents opened, 14 days', 'เหตุการณ์ที่เปิด 14 วัน')"><UiIcon name="chevron_left" :size="12" class="up" /><b>{{ trend.opened }}</b> {{ t("opened", "เปิด") }}</span>
              <span :title="t('Incidents resolved, 14 days', 'เหตุการณ์ที่แก้แล้ว 14 วัน')"><UiIcon name="chevron_left" :size="12" class="down" /><b>{{ trend.resolved }}</b> {{ t("resolved", "แก้แล้ว") }}</span>
            </div>
          </div>
          <svg :viewBox="`0 0 ${trend.W} ${trend.H}`" preserveAspectRatio="none" class="spark" role="img" :aria-label="t('Incidents over the last 14 days', 'เหตุการณ์ 14 วันที่ผ่านมา')">
            <defs><linearGradient id="sparkfill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="var(--c-viz)" stop-opacity="0.55" /><stop offset="1" stop-color="var(--c-viz)" stop-opacity="0" /></linearGradient></defs>
            <polygon :points="trend.area" fill="url(#sparkfill)" /><polyline :points="trend.line" class="spark__l" vector-effect="non-scaling-stroke" />
          </svg>
          <router-link to="/network" class="rail" :aria-label="t('Open the Fleet', 'เปิดฟลีต')"><UiIcon name="chevron_right" :size="18" /></router-link>
        </section>

        <!-- action cards, each with its own dot art -->
        <section class="card act">
          <UiDotArt variant="wave" class="art art--wave" from="#6e54e8" via="#3f8fe0" to="#2b4fa8" :seed="1" />
          <h3>{{ t("Service map", "แผนผังบริการ") }}</h3>
          <p class="sub">{{ t("Every hop a request takes", "ทุกจุดที่คำขอผ่าน") }}</p>
          <p class="state"><UiStatusDot :tone="svc.affected ? 'bad' : 'ok'" :size="9" />{{ svc.affected ? t("Problems on the map", "มีจุดผิดปกติ") : t("All paths healthy", "ทุกเส้นทางปกติ") }}</p>
          <UiButton variant="tint" to="/map" chevron>{{ t("Open map", "เปิดแผนผัง") }}</UiButton>
        </section>
        <section class="card act">
          <UiDotArt variant="wave" class="art art--wave2" from="#f2a37a" via="#b77ce8" to="#5a5bd8" :seed="4" fade="left" />
          <h3>{{ t("Investigate", "สืบสวน") }}</h3>
          <p class="sub">{{ t("Ask the AI to look again", "ให้ AI ดูใหม่อีกรอบ") }}</p>
          <p class="state"><UiStatusDot :tone="investigatingList.length ? 'info' : 'ok'" :size="9" />{{ investigatingList.length ? t(`${investigatingList.length} in progress`, `กำลังทำ ${investigatingList.length}`) : t("Idle", "ว่าง") }}</p>
          <UiButton variant="tint" to="/problems" chevron>{{ t("Incidents", "เหตุการณ์") }}</UiButton>
        </section>

        <!-- the switches that matter -->
        <section class="card prefs">
          <h3>{{ t("Platform settings", "ตั้งค่าแพลตฟอร์ม") }}</h3>
          <template v-if="settings">
            <p class="prefs__sec">{{ t("Investigation", "การสืบสวน") }}</p>
            <div class="pref"><span>{{ t("Investigate new incidents automatically", "สืบสวนเหตุการณ์ใหม่อัตโนมัติ") }}</span>
              <UiSwitch :model-value="settings.auto_analyze === '1'" :label="t('Investigate automatically', 'สืบสวนอัตโนมัติ')" @update:model-value="(v) => saveSetting('auto_analyze', v ? '1' : '0')" /></div>
            <div class="pref"><span>{{ t("Teams alerts", "แจ้งเตือน Teams") }}</span><span class="muted">{{ settings.teams_webhook ? t("On", "เปิด") : t("Not set", "ยังไม่ตั้ง") }}</span></div>
            <p class="prefs__sec">{{ t("Detection", "การตรวจจับ") }}</p>
            <UiSegmented :model-value="settings.sensitivity || 'normal'" :options="SENS" :label="t('Sensitivity', 'ความไว')" @update:model-value="(v) => saveSetting('sensitivity', v)" />
            <div class="pref"><span>{{ t("Re-read cloud accounts", "อ่านบัญชีคลาวด์ใหม่ทุก") }}</span><span class="muted">{{ Math.round((settings.cloud_sync_s || 300) / 60) }} {{ t("min", "นาที") }}</span></div>
          </template>
          <UiButton variant="tint" block to="/settings" chevron class="prefs__all">{{ t("All settings", "การตั้งค่าทั้งหมด") }}</UiButton>
        </section>

        <section class="card act">
          <UiDotArt variant="sphere" class="art art--sphere" from="#3f8fe0" via="#7a62e6" to="#d9a0f0" :seed="1" fade="left" />
          <h3>{{ t("Connect", "เชื่อมต่อ") }}</h3>
          <p class="sub">{{ t("A server, an app, a website or a cloud", "เครื่อง แอป เว็บไซต์ หรือคลาวด์") }}</p>
          <p class="state"><UiStatusDot :tone="fleet && fleet.clouds.length ? 'ok' : 'neutral'" :size="9" />{{ fleet ? t(`${fleet.clouds.length} cloud account${fleet.clouds.length === 1 ? "" : "s"}`, `${fleet.clouds.length} บัญชีคลาวด์`) : "–" }}</p>
          <UiButton variant="tint" to="/connect" chevron>{{ t("Connect", "เชื่อมต่อ") }}</UiButton>
        </section>
        <section class="card act">
          <UiDotArt variant="sphere" class="art art--sphere2" from="#2fc98b" via="#3f8fe0" to="#6e54e8" :seed="3" fade="left" />
          <h3>{{ t("Runbooks", "คู่มือแก้ไข") }}</h3>
          <p class="sub">{{ t("Fixes that worked, reused", "วิธีแก้ที่ได้ผล นำมาใช้ซ้ำ") }}</p>
          <p class="state"><UiStatusDot tone="ok" :size="9" />{{ t("Learning from ratings", "เรียนรู้จากคะแนน") }}</p>
          <UiButton variant="tint" to="/runbooks" chevron>{{ t("Runbooks", "คู่มือแก้ไข") }}</UiButton>
        </section>

        <!-- the queue -->
        <section class="card queue">
          <div class="queue__h"><h3>{{ t("Incident queue", "คิวเหตุการณ์") }}</h3><router-link to="/problems" class="link">{{ t("All incidents", "ทั้งหมด") }}</router-link></div>
          <div v-if="queue.length" class="rows">
            <div v-for="i in queue.slice(0, 5)" :key="i.id" class="row-i" @click="$router.push(`/problems/${i.id}`)">
              <span class="row-i__ic"><UiGlyph :name="INCIDENT_KIND[i.kind]?.glyph || 'inc_error'" :size="24" /></span>
              <div class="row-i__b">
                <div class="row-i__t"><b>{{ kindLabel(i) }}</b> <span class="muted">{{ t("on", "ที่") }} {{ entityOf(i) }}</span></div>
                <div class="row-i__s">P-{{ i.id }} · {{ ago(i.detected_at) }}<template v-if="i.root_cause"> · {{ i.root_cause }}</template></div>
              </div>
              <SeverityPill :severity="i.severity" />
              <StatusPill :status="i.status" />
              <UiButton :variant="i.status === 'awaiting_approval' ? 'primary' : 'tint'" size="sm" :to="`/problems/${i.id}`" chevron @click.stop>
                {{ i.status === "awaiting_approval" ? t("Review", "ดู") : t("Open", "เปิด") }}</UiButton>
            </div>
          </div>
          <div v-else class="clear"><UiStatusDot tone="ok" :size="10" /><span>{{ t("Nothing needs you. The AI opens an incident the moment something drifts.", "ไม่มีอะไรต้องทำ AI จะเปิดเหตุการณ์ทันทีที่มีอะไรผิดปกติ") }}</span></div>
        </section>
      </div>
    </template>
    <UiWait v-else :title="t('Loading the overview', 'กำลังโหลดภาพรวม')" />
  </div>
</template>
<style scoped>
.board { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }
.card { position: relative; overflow: hidden; background: var(--surface); border-radius: 20px; box-shadow: var(--shadow-card); padding: 24px 26px; min-width: 0; isolation: isolate; }
.card > :not(.art):not(.rail) { position: relative; z-index: 1; }
.card h3 { font-size: 24px; font-weight: var(--fw-semibold); letter-spacing: -0.02em; line-height: 1.2; }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 4px; }
.state { display: flex; align-items: center; gap: 9px; margin-top: 12px; font-weight: var(--fw-semibold); font-size: 15px; }
.muted { color: var(--c-text-2); }
/* the halftone art sits at the card's edge, behind the words */
.art { z-index: 0; opacity: 0.95; }
.art--orb { right: -150px; top: -60px; width: 105%; height: 80%; opacity: 0.6; }
.art--wave, .art--wave2 { right: -30px; bottom: -40px; width: 75%; height: 120%; }
.art--sphere, .art--sphere2 { right: -50px; bottom: -70px; width: 70%; height: 150%; opacity: 0.8; }
/* the right-edge chevron rail every resource card carries */
.rail { position: absolute; top: 0; right: 0; bottom: 0; width: 46px; display: grid; place-items: center; color: var(--c-text-3); z-index: 2;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.012), rgba(255, 255, 255, 0.03)); box-shadow: inset 1px 0 0 rgba(255, 255, 255, 0.05); }
.rail:hover { background: var(--c-hover); color: var(--c-text); }
.metric, .mini, .fleet { padding-right: 66px; display: flex; flex-direction: column; justify-content: space-between; gap: 22px; }
.mini { padding: 24px 54px 24px 24px; } .mini .rail { width: 36px; }
.mini .state { white-space: nowrap; }

.welcome { grid-column: span 4; grid-row: span 2; display: flex; flex-direction: column; }
.welcome__k { color: var(--c-text-3); font-size: 15px; }
.welcome__h { font-size: var(--fs-hero); font-weight: var(--fw-bold); letter-spacing: -0.035em; line-height: 1.02; margin-top: 4px; max-width: 9ch; }
.t-action .welcome__h { color: var(--c-warn-text); }
.checks { list-style: none; padding: 0; margin: auto 0 0; display: flex; flex-direction: column; gap: 14px; padding-top: 28px; }
.checks li { display: flex; gap: 12px; align-items: flex-start; } .checks li .ui-dot { margin-top: 5px; }
.checks b { display: block; font-weight: var(--fw-semibold); font-size: 15px; } .checks span { font-size: var(--fs-sm); color: var(--c-text-3); }
.welcome__go { align-self: flex-end; margin-top: 22px; }

.metric { grid-column: span 4; }
.metric__top { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.mini { grid-column: span 2; }
.fleet { grid-column: span 4; gap: 6px; }
.fleet__top { display: flex; justify-content: space-between; gap: 12px; }
.fleet__nums { display: flex; gap: 14px; font-size: var(--fs-sm); color: var(--c-text-3); white-space: nowrap; }
.fleet__nums span { display: inline-flex; align-items: center; gap: 3px; } .fleet__nums b { color: var(--c-text); }
.up { transform: rotate(90deg); color: var(--c-text); } .down { transform: rotate(-90deg); color: var(--c-text); }
.spark { width: 100%; height: 110px; display: block; margin-top: auto; }
.spark__l { fill: none; stroke: var(--c-viz-hi); stroke-width: 1.6; stroke-linejoin: round; }

.act { grid-column: span 4; min-height: 196px; display: flex; flex-direction: column; align-items: flex-start; }
.act .ui-btn { margin-top: auto; }
.act .state { margin-bottom: 22px; }

.prefs { grid-column: span 4; grid-row: span 2; display: flex; flex-direction: column; gap: 14px; }
.prefs__sec { font-size: 10.5px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.09em; color: var(--c-text-3); margin-top: 8px; }
.pref { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 15px; }
.prefs__all { margin-top: auto; }

.queue { grid-column: span 12; }
.queue__h { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
.link { font-size: var(--fs-sm); font-weight: var(--fw-semibold); }
.rows { display: flex; flex-direction: column; }
.row-i { display: flex; align-items: center; gap: 14px; padding: 14px 4px; border-top: 1px solid var(--c-separator); cursor: pointer; }
.row-i:first-child { border-top: 0; }
.row-i:hover .row-i__t b { color: var(--c-primary); }
.row-i__b { flex: 1; min-width: 0; }
.row-i__ic { width: 42px; height: 42px; flex: none; border-radius: 13px; display: grid; place-items: center; background: var(--c-fill);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05); }
.row-i :deep(.stage) { flex: none; }
.row-i__s { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.clear { display: flex; align-items: center; gap: 12px; padding: 22px 4px; color: var(--c-text-2); }

@media (max-width: 1280px) {
  .welcome { grid-column: span 6; grid-row: span 1; } .metric { grid-column: span 6; } .mini { grid-column: span 3; } .fleet { grid-column: span 6; }
  .act { grid-column: span 6; } .prefs { grid-column: span 12; grid-row: auto; }
}
@media (max-width: 760px) {
  .board { grid-template-columns: 1fr; }
  .welcome, .metric, .mini, .fleet, .act, .queue, .prefs { grid-column: auto; }
  .welcome__h { font-size: 36px; } .row-i__s { white-space: normal; }
}
</style>
