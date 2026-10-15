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

// a dense vital-signs strip: tight metric cells, a deliberate contrast to the roomy hero above it
const vitals = computed(() => {
  const s = rollup(app.services), h = rollup(app.hosts);
  const n = awaitingList.value.length, m = investigatingList.value.length;
  return [
    { k: t("Awaiting you", "รอคุณ"), v: n, sub: n ? t("needs approval", "รออนุมัติ") : t("all clear", "เคลียร์หมด"), tone: n ? "action" : "ok", to: "/problems" },
    { k: t("Investigating", "กำลังสืบสวน"), v: m, sub: t("AI working", "AI ทำงาน"), tone: m ? "info" : "muted", to: "/problems" },
    { k: t("Services", "บริการ"), v: `${s.total - s.affected}/${s.total}`, sub: s.affected ? t(`${s.affected} with problems`, `มีปัญหา ${s.affected}`) : t("all healthy", "ปกติ"), tone: s.affected ? "bad" : "ok", to: "/services" },
    { k: t("Hosts", "เครื่อง"), v: `${h.total - h.affected}/${h.total}`, sub: h.affected ? t(`${h.affected} to check`, `ต้องดู ${h.affected}`) : t("all healthy", "ปกติ"), tone: h.affected ? "bad" : "ok", to: "/network" },
    { k: t("Avg fix", "เวลาแก้เฉลี่ย"), v: dur(app.kpi.mttr_s), sub: t("detect → verified", "ตรวจพบ → ยืนยัน"), tone: "none", to: "/problems" },
    { k: t("Coverage", "ครอบคลุม"), v: coverage.value ? `${coverage.value.monitored}/${coverage.value.total}` : "—",
      sub: coverage.value?.suggest ? t(`connect ${coverage.value.suggest} more`, `เชื่อมอีก ${coverage.value.suggest}`) : t("machines", "เครื่อง"), tone: "none", to: "/network" },
  ];
});

const kindLabel = (i) => INCIDENT_KIND[i.kind]?.label || i.title;
const entityOf = (i) => i.entity_name || i.entity;
const eyebrow = computed(() => (status.value.tone === "action" ? t("Action required", "ต้องดำเนินการ")
  : status.value.tone === "info" ? t("AI investigating", "AI กำลังสืบสวน") : t("All systems normal", "ระบบทำงานปกติ")));
</script>
<template>
  <div class="page">
    <template v-if="app.overview">
      <!-- page header: status eyebrow, headline, and the one next action -->
      <header :class="['top', `top--${status.tone}`]" aria-live="polite">
        <div class="top__l">
          <span class="eyebrow"><span class="eyebrow__dot" />{{ eyebrow }}</span>
          <h1>{{ status.title }}</h1>
          <p class="sub">{{ status.sub }}</p>
        </div>
        <div class="top__r">
          <UiButton :variant="primary.variant" size="lg" :to="primary.to" :icon="primary.icon">{{ primary.label }}</UiButton>
          <span class="checked">{{ t("Checked", "ตรวจเมื่อ") }} {{ ago(app.overview.detector?.ts) }}</span>
        </div>
      </header>

      <!-- dense vital-signs strip: tight numeric cells divided by hairlines (density contrast to the hero) -->
      <div class="vitals">
        <router-link v-for="v in vitals" :key="v.k" :to="v.to" class="vital">
          <span class="vital__k">{{ v.k }}</span>
          <b :class="['vital__v', `t-${v.tone}`]">{{ v.v }}</b>
          <span class="vital__s">{{ v.sub }}</span>
        </router-link>
      </div>

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

      </div>
    </template>
    <UiWait v-else :title="t('Loading the overview', 'กำลังโหลดภาพรวม')" />
  </div>
</template>
<style scoped>
/* ---- page header: editorial, not a coloured alert box. Status reads from a small eyebrow dot + the CTA. ---- */
.top { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; padding: 20px 0 20px; margin-bottom: 22px; border-bottom: 1px solid var(--c-border); }
.top__l { min-width: 0; }
.eyebrow { display: inline-flex; align-items: center; gap: 7px; font-size: var(--fs-xs); font-weight: var(--fw-semibold); text-transform: uppercase;
  letter-spacing: 0.06em; color: var(--c-text-3); margin-bottom: 11px; }
.eyebrow__dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c-neutral); flex: none; }
.top--action .eyebrow { color: var(--c-action-text); } .top--action .eyebrow__dot { background: var(--c-action); }
.top--info .eyebrow { color: var(--c-primary); } .top--info .eyebrow__dot { background: var(--c-primary); animation: eb-pulse 2s var(--ease, ease-out) infinite; }
.top--ok .eyebrow { color: var(--c-ok-text); } .top--ok .eyebrow__dot { background: var(--c-ok); }
@keyframes eb-pulse { 0% { box-shadow: 0 0 0 0 var(--c-halo); } 70%, 100% { box-shadow: 0 0 0 6px transparent; } }
@media (prefers-reduced-motion: reduce) { .top--info .eyebrow__dot { animation: none; } }
.top h1 { font-size: var(--fs-3xl); line-height: 1.15; font-weight: var(--fw-bold); letter-spacing: -0.01em; }
.sub { color: var(--c-text-2); margin-top: 6px; max-width: 72ch; }
.top__r { display: flex; flex-direction: column; align-items: flex-end; gap: 8px; flex: none; }
.checked { font-size: var(--fs-xs); color: var(--c-text-3); white-space: nowrap; }

/* ---- dense vital-signs strip: one tight card, cells divided by vertical hairlines ---- */
.vitals { display: flex; background: var(--c-surface); box-shadow: var(--shadow-card); border-radius: var(--radius-lg); overflow: hidden; margin-bottom: 20px; }
.vital { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; padding: 12px 16px; text-decoration: none; color: var(--c-text);
  border-left: 1px solid var(--c-separator); }
.vital:first-child { border-left: 0; }
.vital:hover { background: var(--c-hover); }
.vital__k { font-size: 11px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text-3); }
.vital__v { font-size: var(--fs-2xl); font-weight: var(--fw-bold); font-variant-numeric: tabular-nums; line-height: 1.15; letter-spacing: -0.02em; }
.vital__s { font-size: var(--fs-xs); color: var(--c-text-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.vital__v.t-ok { color: var(--c-text); } .vital__v.t-bad { color: var(--c-bad-text); }
.vital__v.t-action { color: var(--c-action-text); } .vital__v.t-info { color: var(--c-primary); }
@media (max-width: 900px) { .vitals { flex-wrap: wrap; } .vital { flex: 1 1 33%; border-top: 1px solid var(--c-separator); } .vital:nth-child(-n+3) { border-top: 0; } }
@media (max-width: 520px) { .vital { flex-basis: 50%; } }

/* ---- main column: the incident queue, full width ---- */
.cmd { display: block; }
.cmd__main { min-width: 0; }

/* group heading */
.grp { display: flex; align-items: center; gap: 8px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); margin: 0 0 8px; }
.grp .ui-icon { color: var(--c-text-3); }
.grp__n { font-size: var(--fs-xs); font-weight: var(--fw-semibold); color: var(--c-text-2); background: var(--c-fill); border-radius: var(--radius-pill); padding: 1px 9px; }
.list + .grp { margin-top: 22px; }

/* incident list: one clean card, rows divided by hairlines, highlighted on hover - no heavy coloured bars */
.list { background: var(--c-surface); box-shadow: var(--shadow-card); border-radius: var(--radius-lg); overflow: hidden; }
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
  background: var(--c-surface); box-shadow: var(--shadow-card); border-radius: var(--radius-lg); }
.clear__mark { width: 48px; height: 48px; border-radius: 50%; display: grid; place-items: center; background: var(--c-ok-bg); color: var(--c-ok-text); margin-bottom: 4px; }
.clear b { font-size: var(--fs-lg); } .clear .muted { max-width: 42ch; }

/* right column panels */
.cmd__aside { display: flex; flex-direction: column; gap: 14px; position: sticky; top: 12px; }
.panel { background: var(--c-surface); box-shadow: var(--shadow-card); border-radius: var(--radius-lg); padding: 16px 18px; }
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
@media (max-width: 760px) { .top { flex-direction: column; align-items: stretch; gap: 16px; } .top__r { align-items: stretch; } .top h1 { font-size: 23px; } .item__s { white-space: normal; } }
</style>
