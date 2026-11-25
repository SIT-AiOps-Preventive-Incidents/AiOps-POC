<script setup>
import { computed } from "vue";
import { usePageFacts } from "@/composables/usePageFacts";
import { dashboardTone, overviewFacts, overviewSnapshot, priorityIncidents } from "@/lib/dashboard";
import { factLabel } from "@/lib/pageSummary";
import { useI18n } from "@/lib/i18n";
import { INCIDENT_KIND } from "@/lib/vocab";
import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";

const app = useAppStore();
const auth = useAuthStore();
const { locale, t } = useI18n();
const snapshot = computed(() => app.overview ? overviewSnapshot(app.overview, app.lastLoaded / 1000) : null);
const incidents = computed(() => priorityIncidents(app.openProblems).slice(0, 4));
const updated = computed(() => new Intl.DateTimeFormat(locale.value === "th" ? "th-TH" : "en-GB", {
  hour: "2-digit", minute: "2-digit", second: "2-digit",
}).format(app.lastLoaded));
const tones = computed(() => ({
  stale: { tone: "warn", title: t("Showing the last update", "กำลังแสดงข้อมูลครั้งล่าสุด"),
    text: t("The latest refresh failed. The figures below may have changed.", "อัปเดตล่าสุดไม่สำเร็จ ตัวเลขด้านล่างอาจเปลี่ยนไปแล้ว") },
  attention: { tone: "warn", title: t("Some items need attention", "มีรายการที่ต้องติดตาม"),
    text: t("Review reported issues and any proposed fixes waiting for a decision.", "ดูปัญหาที่ระบบรายงานและวิธีแก้ที่รอการตัดสินใจ") },
  active: { tone: "info", title: t("There are open incidents", "มีเหตุการณ์ที่ยังเปิดอยู่"),
    text: t("See where each incident stands and what is being worked on.", "ดูว่าแต่ละเหตุการณ์อยู่ขั้นไหนและระบบกำลังทำอะไร") },
  limited: { tone: "neutral", title: t("System status is partly unknown", "ยังยืนยันสถานะของระบบได้ไม่ครบ"),
    text: t("Some monitoring data or recent checks are missing. Check the coverage below.", "ข้อมูลการเฝ้าดูหรือผลตรวจล่าสุดยังไม่ครบ ดูรายละเอียดด้านล่าง") },
  healthy: { tone: "ok", title: t("Monitored systems look healthy", "ระบบที่เฝ้าดูทำงานปกติ"),
    text: t("No open incidents or reported issues in the latest check.", "ผลตรวจล่าสุดไม่พบเหตุการณ์ที่ยังเปิดอยู่หรือปัญหาที่รายงาน") },
}));
const hero = computed(() => snapshot.value && tones.value[dashboardTone(snapshot.value, app.error)]);

function coverage({ total, affected, quiet }) {
  if (!total) return t("Nothing monitored yet", "ยังไม่มีรายการที่เฝ้าดู");
  return t(`${affected} with issues · ${quiet} without data`, `มีปัญหา ${affected} · ขาดข้อมูล ${quiet}`);
}

const metrics = computed(() => {
  const { open, awaiting, services, hosts } = snapshot.value;
  return [
    { title: t("Open incidents", "เหตุการณ์ที่ยังเปิดอยู่"), value: open, note: t("Incidents still on the list", "เหตุการณ์ที่ยังไม่สิ้นสุด"),
      icon: "warning", tone: open ? "bad" : "neutral", to: "/problems" },
    { title: t("Waiting for approval", "รออนุมัติวิธีแก้"), value: awaiting, note: t("The owner makes the decision", "เจ้าของระบบเป็นผู้ตัดสินใจ"),
      icon: "clock", tone: awaiting ? "warn" : "neutral", to: "/problems" },
    { title: t("Healthy services", "บริการที่ทำงานปกติ"), value: services.healthy, total: services.total, note: coverage(services),
      icon: "cube", tone: services.affected ? "bad" : services.quiet || !services.total ? "neutral" : "ok", to: "/services" },
    { title: t("Healthy hosts", "เครื่องที่ทำงานปกติ"), value: hosts.healthy, total: hosts.total, note: coverage(hosts),
      icon: "server", tone: hosts.affected ? "bad" : hosts.quiet || !hosts.total ? "neutral" : "ok", to: "/computers" },
  ];
});
const activity = computed(() => [
  { key: "ai_investigations", value: snapshot.value.analyzing },
  { key: "fixes_in_progress", value: snapshot.value.fixing },
  { key: "failed_fixes", value: snapshot.value.failed },
]);
const incidentTitle = (i) => factLabel(`issue_${i.kind}`, t) || t(i.title, "พบความผิดปกติ");
const retry = () => app.load().catch(() => {});
usePageFacts(() => overviewFacts(snapshot.value, app.error));
</script>

<template>
  <div class="page page--wide dashboard" :lang="locale">
    <UiPageHeader :title="t('Dashboard', 'สรุปสถานะระบบ')"
                  :subtitle="t('System health, open incidents and work in progress.', 'ดูสถานะระบบ เหตุการณ์ที่ยังเปิดอยู่ และงานที่กำลังดำเนินการ')" />

    <template v-if="snapshot">
      <section :class="['panel', 'hero', `tone-${hero.tone}`]" aria-labelledby="dashboard-status">
        <UiDotArt variant="sphere" class="hero__art" from="var(--c-viz)" via="var(--c-ai)" to="var(--c-ok)" :seed="2" />
        <div class="hero__content">
          <div class="hero__meta">
            <span class="hero__status"><UiStatusDot :tone="hero.tone" :size="8" />{{ t("System status", "สถานะระบบ") }}</span>
            <time :datetime="new Date(app.lastLoaded).toISOString()">{{ t("Updated", "อัปเดต") }} {{ updated }}</time>
          </div>
          <h2 id="dashboard-status">{{ hero.title }}</h2>
          <p>{{ hero.text }}</p>
          <div class="hero__actions">
            <UiButton v-if="app.error" variant="tint" size="lg" :loading="app.loading" @click="retry">{{ t("Refresh", "อัปเดตอีกครั้ง") }}</UiButton>
            <UiButton v-else-if="snapshot.open" size="lg" to="/problems" chevron>{{ t("View incidents", "ดูเหตุการณ์") }}</UiButton>
            <UiButton v-else-if="!snapshot.services.total && !snapshot.hosts.total && auth.can('fleet.connect')" size="lg" to="/connect" chevron>{{ t("Connect to monitoring", "เชื่อมต่อระบบที่ต้องการเฝ้าดู") }}</UiButton>
            <UiButton variant="tint" size="lg" to="/overview" chevron>{{ t("Technical overview", "ภาพรวมเชิงเทคนิค") }}</UiButton>
          </div>
        </div>
      </section>

      <section class="metrics" :aria-label="t('Key figures', 'ตัวเลขสำคัญ')">
        <router-link v-for="m in metrics" :key="m.title" :to="m.to" :class="['panel', 'metric', `tone-${m.tone}`]">
          <div class="metric__head"><span class="metric__icon"><UiIcon :name="m.icon" :size="19" /></span><UiIcon name="chevron_right" :size="16" /></div>
          <h2>{{ m.title }}</h2>
          <p class="metric__value num">{{ m.value }}<span v-if="m.total != null"> / {{ m.total }}</span></p>
          <p class="muted">{{ m.note }}</p>
        </router-link>
      </section>

      <div class="details">
        <section class="panel section" aria-labelledby="dashboard-incidents">
          <div class="section__head">
            <h2 id="dashboard-incidents">{{ t("Incidents to watch", "เหตุการณ์ที่ควรติดตาม") }}</h2>
            <UiButton variant="ghost" size="lg" to="/problems" chevron>{{ t("View all", "ดูทั้งหมด") }}</UiButton>
          </div>
          <ul v-if="incidents.length" class="incident-list">
            <li v-for="i in incidents" :key="i.id">
              <router-link class="incident" :to="`/problems/${i.id}`">
                <span class="incident__icon"><UiIcon :name="INCIDENT_KIND[i.kind]?.icon || 'warning'" :size="19" /></span>
                <span class="incident__text"><b>{{ incidentTitle(i) }}</b><span class="muted">{{ i.entity_name || i.entity }} · P-{{ i.id }}</span></span>
                <span class="incident__stage" :class="{ warn: i.status === 'awaiting_approval', bad: i.status === 'remediation_failed' }">{{ factLabel(`incident_${i.status}`, t) || t("Status unknown", "ไม่ทราบสถานะ") }}</span>
                <UiIcon name="chevron_right" :size="16" class="muted" />
              </router-link>
            </li>
          </ul>
          <div v-else class="empty muted"><UiIcon name="checkmark_circle" :size="24" />{{ t("No open incidents in the latest update.", "ไม่พบเหตุการณ์ที่ยังเปิดอยู่ในข้อมูลล่าสุด") }}</div>
        </section>

        <section class="panel section" aria-labelledby="dashboard-work">
          <div class="section__head work__head"><h2 id="dashboard-work">{{ t("What the system is doing", "ระบบกำลังทำอะไร") }}</h2></div>
          <dl class="activity">
            <div v-for="a in activity" :key="a.key"><dt>{{ factLabel(a.key, t) }}</dt><dd class="num">{{ a.value }}</dd></div>
          </dl>
          <div class="signals">
            <span><UiStatusDot :tone="snapshot.detectionLive ? 'ok' : 'neutral'" :size="8" />{{ snapshot.detectionLive ? t("Monitoring active", "กำลังเฝ้าดูระบบ") : t("No recent check confirmed", "ยังไม่พบผลตรวจล่าสุด") }}</span>
            <span><UiStatusDot :tone="snapshot.aiReady ? 'ok' : 'neutral'" :size="8" />{{ snapshot.aiReady ? t("AI available", "AI พร้อมใช้งาน") : t("AI availability unconfirmed", "ยังไม่ยืนยันว่า AI พร้อมใช้งาน") }}</span>
          </div>
        </section>
      </div>
    </template>

    <div v-else-if="app.error" class="panel empty" role="status">
      <p>{{ t("System status could not be loaded.", "โหลดสถานะระบบไม่ได้") }}</p>
      <UiButton variant="tint" size="lg" :loading="app.loading" @click="retry">{{ t("Try again", "ลองอีกครั้ง") }}</UiButton>
    </div>
    <UiSkeletonPage v-else :header="false" :rows="4" />
  </div>
</template>

<style scoped>
.dashboard { --dashboard-gap: var(--sp-4); color: var(--c-text); }
.panel { background: var(--surface); border-radius: var(--radius-xl); box-shadow: var(--shadow-card); min-inline-size: 0; }
.tone-neutral { --tone-text: var(--c-text-2); --tone-bg: var(--c-fill); }
.tone-ok { --tone-text: var(--c-ok-text); --tone-bg: var(--c-ok-bg); }
.tone-warn { --tone-text: var(--c-warn-text); --tone-bg: var(--c-warn-bg); }
.tone-info { --tone-text: var(--c-info-text); --tone-bg: var(--c-info-bg); }
.tone-bad { --tone-text: var(--c-bad-text); --tone-bg: var(--c-bad-bg); }
.hero { position: relative; isolation: isolate; overflow: hidden; padding: clamp(20px, 4vw, 44px); }
.hero::before { content: ""; position: absolute; inset: 0; z-index: -1; background: radial-gradient(ellipse at 100% 20%, var(--c-ai-bg), transparent 72%); }
.hero__art { z-index: -1; inset: 0 0 0 auto; width: min(58%, 660px); height: 100%; opacity: .68; }
.hero__content { max-width: 650px; }
.hero__meta, .hero__actions { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2) var(--sp-3); }
.hero__meta { color: var(--c-text-2); font-size: var(--fs-sm); }
.hero__status { display: inline-flex; align-items: center; gap: var(--sp-2); padding: var(--sp-1) var(--sp-3); border-radius: var(--radius-pill); background: var(--tone-bg); color: var(--tone-text); font-weight: var(--fw-semibold); }
.hero h2 { font-size: clamp(var(--fs-2xl), 3.7vw, var(--fs-hero)); line-height: var(--lh-tight); margin: var(--sp-4) 0 var(--sp-2); text-wrap: balance; }
.hero p { font-size: var(--fs-lg); color: var(--c-text-2); max-width: 49ch; }
.hero__actions { margin-top: var(--sp-5); }
.hero__actions > :deep(.ui-btn) { white-space: normal; text-align: center; }
.hero__actions > :deep(.ui-btn--primary) { background: light-dark(var(--c-primary-tint), var(--c-primary)); color: light-dark(var(--c-action-text), var(--c-on-primary)); }
.metrics, .details { display: grid; gap: var(--dashboard-gap); margin-top: var(--dashboard-gap); }
.metrics { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.metric { padding: var(--sp-4); color: var(--c-text); transition: box-shadow var(--dur-fast) var(--ease); }
.metric:hover, .incident:hover { box-shadow: inset 0 0 0 1px var(--c-border), var(--shadow-card); background: var(--c-raised); }
.metric__head { display: flex; align-items: center; justify-content: space-between; color: var(--c-text-2); margin-bottom: var(--sp-3); }
.metric__icon, .incident__icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: var(--radius-md); color: var(--tone-text, var(--c-info-text)); background: var(--tone-bg, var(--c-info-bg)); }
.metric h2 { font-size: var(--fs-md); }
.metric__value { font-size: var(--fs-3xl); font-weight: var(--fw-bold); line-height: 1.2; margin: var(--sp-1) 0; }
.metric__value span { color: var(--c-text-2); font-size: var(--fs-lg); }
.metric .muted { font-size: var(--fs-sm); }
.details { grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr); align-items: start; }
.section { padding: var(--sp-4) var(--sp-5) var(--sp-5); }
.section__head { min-height: 44px; display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0 var(--sp-2); margin-bottom: var(--sp-2); }
.section__head h2 { font-size: var(--fs-xl); }
.section__head > :deep(.ui-btn) { padding-inline: var(--sp-2); }
.incident-list { list-style: none; margin: 0; padding: 0; }
.incident { display: grid; grid-template-columns: auto minmax(0, 1fr) auto auto; gap: var(--sp-3); align-items: center; padding: var(--sp-2); color: var(--c-text); border-radius: var(--radius-md); }
.incident__text { display: grid; overflow-wrap: anywhere; }
.incident__text .muted, .incident__stage { font-size: var(--fs-sm); }
.incident__stage { color: var(--c-info-text); }
.incident__stage.warn { color: var(--c-warn-text); }
.incident__stage.bad { color: var(--c-bad-text); }
.activity { margin: 0; }
.activity > div { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); min-height: 38px; border-bottom: 1px solid var(--c-separator); }
.activity dd { margin: 0; font-weight: var(--fw-semibold); }
.signals { display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-4); margin-top: var(--sp-3); color: var(--c-text-2); font-size: var(--fs-sm); }
.signals span, .empty { display: flex; align-items: center; gap: var(--sp-2); }
.empty { flex-wrap: wrap; padding: var(--sp-4); }
@media (max-width: 1100px) {
  .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .details { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .hero__art { opacity: .2; }
  .section { padding-inline: var(--sp-3); }
}
@media (max-width: 430px) {
  .dashboard { --dashboard-gap: var(--sp-3); }
  .incident { grid-template-columns: auto minmax(0, 1fr) auto; gap: var(--sp-1) var(--sp-2); }
  .incident__icon { grid-row: span 2; }
  .incident__stage { grid-row: 2; grid-column: 2; }
  .incident > .ui-icon:last-child { grid-row: 1 / span 2; grid-column: 3; }
}
</style>
