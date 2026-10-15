<script setup>
// Overview = a command centre. One hero (state + the single next action), then two zones:
//   left  = what needs me now (the incident queue, grouped: approve first, then investigating)
//   right = how is everything (system health + fleet coverage), as a quiet summary that links out.
// The long per-service / per-host tables live on their own pages; here we summarise and link.
import { computed, ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago, dur } from "@/lib/format";
import { rollup } from "@/lib/insight";
import { INCIDENT_KIND } from "@/lib/vocab";
import { useAppStore } from "@/stores/app";
import { useIncidentStore } from "@/stores/incidents";
import { useI18n } from "@/lib/i18n";
import SeverityPill from "@/components/domain/SeverityPill.vue";

const app = useAppStore();
const incidents = useIncidentStore();
const { t } = useI18n();
usePolling(() => incidents.loadList(), 15000);

const coverage = ref(null);
usePolling(async () => {
  try {
    const [recs, disc] = await Promise.all([api.network.recommendations(), api.network.discovered()]);
    const monitored = app.hosts.length;
    coverage.value = { monitored, total: Math.max(disc.summary.machines, monitored), suggest: recs.count, top: recs.recommendations[0] };
  } catch { coverage.value = null; }
}, 30000);

const awaitingList = computed(() => app.awaiting);
const investigatingList = computed(() => app.openProblems.filter((p) => p.status !== "awaiting_approval"));
const queue = computed(() => [...awaitingList.value, ...investigatingList.value]);
const lastResolved = computed(() => incidents.list.find((i) => i.status === "resolved"));

const status = computed(() => {
  const n = awaitingList.value.length, m = investigatingList.value.length;
  if (n) return { tone: "action", title: n > 1 ? t(`${n} fixes are waiting for your approval`, `มี ${n} การแก้ไขรอคุณอนุมัติ`) : t("A fix is waiting for your approval", "มีการแก้ไขรอคุณอนุมัติ"),
    sub: t("The AI found the cause and tested each fix in a dry run. Nothing changes until you approve.", "AI หาสาเหตุเจอและทดสอบการแก้ไขแต่ละอันแบบ dry run แล้ว ไม่มีอะไรเปลี่ยนจนกว่าคุณจะอนุมัติ") };
  if (m) return { tone: "info", title: m > 1 ? t(`The AI is investigating ${m} incidents`, `AI กำลังสืบสวน ${m} เหตุการณ์`) : t("The AI is investigating an incident", "AI กำลังสืบสวนเหตุการณ์"),
    sub: t("You will be asked to approve a fix as soon as one is ready.", "เมื่อการแก้ไขพร้อม ระบบจะให้คุณอนุมัติ") };
  return { tone: "ok", title: t("Everything is working normally", "ทุกอย่างทำงานปกติ"),
    sub: lastResolved.value ? t(`Last incident resolved ${ago(lastResolved.value.resolved_at || lastResolved.value.detected_at)}.`, `เหตุการณ์ล่าสุดแก้ไขเสร็จ ${ago(lastResolved.value.resolved_at || lastResolved.value.detected_at)}`) : t("No incidents so far.", "ยังไม่มีเหตุการณ์") };
});

// the single most important next action — the hero's button
const primary = computed(() => {
  if (awaitingList.value.length) return { to: `/problems/${awaitingList.value[0].id}`, label: t("Review the first fix", "ดูการแก้ไขแรก"), icon: "checkmark", variant: "action" };
  if (queue.value.length) return { to: `/problems/${queue.value[0].id}`, label: t("Open the incident", "เปิดเหตุการณ์"), icon: "chevron_right", variant: "primary" };
  return { to: "/network", label: t("Open the Fleet", "เปิดฟลีต"), icon: "server", variant: "tint" };
});

// right column: a quiet health summary that links to the detail pages
const health = computed(() => {
  const s = rollup(app.services), h = rollup(app.hosts);
  return [
    { label: t("Services", "บริการ"), icon: "cube", to: "/services", value: `${s.total - s.affected}/${s.total}`,
      sub: s.affected ? t(`${s.affected} with problems`, `มีปัญหา ${s.affected}`) : t("all healthy", "ปกติทั้งหมด"), tone: s.affected ? "bad" : "ok" },
    { label: t("Hosts", "เครื่อง"), icon: "server", to: "/network", value: `${h.total - h.affected}/${h.total}`,
      sub: h.affected ? t(`${h.affected} need attention`, `ต้องดู ${h.affected}`) : t("all healthy", "ปกติทั้งหมด"), tone: h.affected ? "bad" : "ok" },
    { label: t("Avg fix time", "เวลาแก้เฉลี่ย"), icon: "checkmark_circle", to: "/problems", value: dur(app.kpi.mttr_s),
      sub: t("detect → verified", "ตรวจพบ → ยืนยัน"), tone: "none" },
  ];
});

const kindLabel = (i) => INCIDENT_KIND[i.kind]?.label || i.title;
const entityOf = (i) => i.entity_name || i.entity;
const heroIcon = computed(() => (status.value.tone === "ok" ? "checkmark" : status.value.tone === "action" ? "person" : "sparkle"));
</script>
<template>
  <div class="page">
    <template v-if="app.overview">
      <!-- hero: the state + the one next action -->
      <section :class="['hero', `hero--${status.tone}`]" aria-live="polite">
        <span class="hero__mark" aria-hidden="true"><UiIcon :name="heroIcon" :size="22" /></span>
        <div class="hero__text"><h1>{{ status.title }}</h1><p>{{ status.sub }}</p></div>
        <div class="hero__side">
          <UiButton :variant="primary.variant" size="lg" :to="primary.to" :icon="primary.icon">{{ primary.label }}</UiButton>
          <span class="hero__checked">{{ t("Checked", "ตรวจเมื่อ") }} {{ ago(app.overview.detector?.ts) }}</span>
        </div>
      </section>

      <div class="cmd">
        <!-- left: what needs me -->
        <div class="cmd__main">
          <template v-if="awaitingList.length">
            <h2 class="grp"><UiIcon name="person" :size="15" />{{ t("Needs your approval", "รอคุณอนุมัติ") }}<span class="grp__n">{{ awaitingList.length }}</span></h2>
            <div class="list">
              <div v-for="i in awaitingList" :key="i.id" class="item" @click="$router.push(`/problems/${i.id}`)">
                <div class="item__body">
                  <div class="item__t"><b>{{ kindLabel(i) }}</b> <span class="muted">{{ t("on", "ที่") }} {{ entityOf(i) }}</span></div>
                  <div class="item__s">P-{{ i.id }} · {{ ago(i.detected_at) }}<template v-if="i.root_cause"> · <span class="ai">{{ t("AI", "AI") }}</span> {{ i.root_cause }}</template></div>
                </div>
                <SeverityPill :severity="i.severity" />
                <UiButton variant="action" size="sm" :to="`/problems/${i.id}`" @click.stop>{{ t("Review", "ดู") }}</UiButton>
              </div>
            </div>
          </template>

          <template v-if="investigatingList.length">
            <h2 class="grp"><UiIcon name="sparkle" :size="15" />{{ t("AI is investigating", "AI กำลังสืบสวน") }}<span class="grp__n">{{ investigatingList.length }}</span></h2>
            <div class="list">
              <div v-for="i in investigatingList" :key="i.id" class="item" @click="$router.push(`/problems/${i.id}`)">
                <div class="item__body">
                  <div class="item__t"><b>{{ kindLabel(i) }}</b> <span class="muted">{{ t("on", "ที่") }} {{ entityOf(i) }}</span></div>
                  <div class="item__s">P-{{ i.id }} · {{ ago(i.detected_at) }}<template v-if="i.root_cause"> · <span class="ai">{{ t("AI", "AI") }}</span> {{ i.root_cause }}</template><template v-else> · {{ t("reading metrics, traces and logs…", "กำลังอ่าน metric, trace และ log…") }}</template></div>
                </div>
                <SeverityPill :severity="i.severity" />
                <UiButton variant="tint" size="sm" :to="`/problems/${i.id}`" @click.stop>{{ t("Open", "เปิด") }}</UiButton>
              </div>
            </div>
          </template>

          <div v-if="!queue.length" class="clear">
            <span class="clear__mark"><UiIcon name="checkmark" :size="24" /></span>
            <b>{{ t("Nothing needs you right now", "ตอนนี้ไม่มีอะไรต้องทำ") }}</b>
            <span class="muted">{{ t("The AI is watching every service and will open an incident the moment something drifts.", "AI เฝ้าทุกบริการอยู่ และจะเปิดเหตุการณ์ทันทีที่มีอะไรผิดปกติ") }}</span>
          </div>
        </div>

        <!-- right: how is everything -->
        <aside class="cmd__aside">
          <div class="panel">
            <div class="panel__h">{{ t("System health", "สุขภาพระบบ") }}</div>
            <router-link v-for="r in health" :key="r.label" :to="r.to" class="hrow">
              <span :class="['hrow__ic', `t-${r.tone}`]"><UiIcon :name="r.icon" :size="16" /></span>
              <span class="hrow__l">{{ r.label }}<small>{{ r.sub }}</small></span>
              <b :class="`t-${r.tone}`">{{ r.value }}</b>
            </router-link>
          </div>

          <router-link v-if="coverage" to="/network" class="panel cov">
            <div class="panel__h">{{ t("Fleet coverage", "ความครอบคลุมฟลีต") }}</div>
            <div class="cov__v"><b>{{ coverage.monitored }}</b><span class="muted">/ {{ coverage.total }} {{ t("machines monitored", "เครื่องที่เฝ้าดู") }}</span></div>
            <div class="cov__bar"><i :style="{ width: `${Math.round((coverage.monitored / Math.max(coverage.total, 1)) * 100)}%` }" /></div>
            <span v-if="coverage.suggest" class="cov__cta">{{ t(`Connect ${coverage.suggest} more`, `เชื่อมเพิ่มอีก ${coverage.suggest} เครื่อง`) }}<UiIcon name="chevron_right" :size="15" /></span>
          </router-link>
        </aside>
      </div>
    </template>
    <UiWait v-else :title="t('Loading the overview', 'กำลังโหลดภาพรวม')" />
  </div>
</template>
<style scoped>
/* ---- hero: the one focal banner ---- */
.hero { display: flex; align-items: center; gap: 16px; padding: 18px 22px 18px 24px; margin: 8px 0 18px; position: relative; overflow: hidden;
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

/* ---- command grid ---- */
.cmd { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 20px; align-items: start; }
.cmd__main { min-width: 0; }

/* group heading */
.grp { display: flex; align-items: center; gap: 8px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); margin: 0 0 8px; }
.grp .ui-icon { color: var(--c-text-3); }
.grp__n { font-size: var(--fs-xs); font-weight: var(--fw-semibold); color: var(--c-text-2); background: var(--c-fill); border-radius: var(--radius-pill); padding: 1px 9px; }
.list + .grp { margin-top: 22px; }

/* incident list: one clean card, rows divided by hairlines, highlighted on hover - no heavy coloured bars */
.list { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow: hidden; }
.item { display: flex; align-items: center; gap: 12px; padding: 13px 16px; border-top: 1px solid var(--c-separator); cursor: pointer; }
.item:first-child { border-top: 0; }
.item:hover { background: var(--c-hover); }
.item__body { flex: 1; min-width: 0; }
.item__t { font-size: var(--fs-md); } .item__t b { font-weight: var(--fw-semibold); }
.item__s { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item__s .ai { color: var(--c-primary); font-weight: var(--fw-semibold); }
.item :deep(.ui-pill) { flex: none; } .item .ui-button { flex: none; }

/* all-clear state */
.clear { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 6px; padding: 48px 24px;
  background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); }
.clear__mark { width: 48px; height: 48px; border-radius: 50%; display: grid; place-items: center; background: var(--c-ok-bg); color: var(--c-ok-text); margin-bottom: 4px; }
.clear b { font-size: var(--fs-lg); } .clear .muted { max-width: 42ch; }

/* right column panels */
.cmd__aside { display: flex; flex-direction: column; gap: 14px; position: sticky; top: 12px; }
.panel { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 14px 16px; }
.panel__h { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); margin-bottom: 10px; }
.hrow { display: flex; align-items: center; gap: 11px; padding: 9px 0; text-decoration: none; color: var(--c-text); border-top: 1px solid var(--c-separator); }
.hrow:first-of-type { border-top: 0; }
.hrow:hover .hrow__l { color: var(--c-primary); }
.hrow__ic { width: 30px; height: 30px; border-radius: var(--radius-md); display: grid; place-items: center; flex: none; background: var(--c-fill); color: var(--c-text-2); }
.hrow__ic.t-ok { background: var(--c-ok-bg); color: var(--c-ok-text); } .hrow__ic.t-bad { background: var(--c-bad-bg); color: var(--c-bad-text); }
.hrow__l { flex: 1; min-width: 0; display: flex; flex-direction: column; font-weight: var(--fw-medium); }
.hrow__l small { font-size: var(--fs-xs); color: var(--c-text-3); font-weight: var(--fw-regular, 400); }
.hrow b { font-size: var(--fs-lg); font-variant-numeric: tabular-nums; }
.t-ok { color: var(--c-ok-text); } .t-bad { color: var(--c-bad-text); }

.cov { display: block; text-decoration: none; color: var(--c-text); }
.cov:hover { border-color: var(--c-primary); }
.cov__v { display: flex; align-items: baseline; gap: 6px; } .cov__v b { font-size: var(--fs-2xl); font-weight: var(--fw-bold); font-variant-numeric: tabular-nums; }
.cov__bar { height: 6px; border-radius: 3px; background: var(--c-fill-2); overflow: hidden; margin: 10px 0; }
.cov__bar i { display: block; height: 100%; background: var(--c-primary); border-radius: 3px; }
.cov__cta { display: inline-flex; align-items: center; gap: 2px; color: var(--c-primary); font-weight: var(--fw-semibold); font-size: var(--fs-sm); }

@media (max-width: 1080px) { .cmd { grid-template-columns: 1fr; } .cmd__aside { position: static; } }
@media (max-width: 760px) { .hero { flex-wrap: wrap; } .hero__text { flex-basis: 100%; } .hero__side { width: 100%; align-items: stretch; } .hero__text h1 { font-size: 20px; } .row__s { white-space: normal; } }
</style>
