<script setup>
import { computed, inject, onBeforeUnmount, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { pageFactsKey } from "@/composables/usePageFacts";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { pageContext, summaryFacts } from "@/lib/pageSummary";

const route = useRoute();
const source = inject(pageFactsKey);
const { locale, t } = useI18n();
const context = computed(() => pageContext(route.matched.at(-1)?.path, t));
const dialog = ref(null);
const button = ref(null);
const facts = ref([]);
const answer = ref("");
const phase = ref("idle");
let requestId = 0;

async function summarize() {
  const id = ++requestId;
  const active = source.value;
  facts.value = summaryFacts(active?.path === route.fullPath ? active.read() ?? {} : {}, t);
  answer.value = "";
  phase.value = "loading";
  try {
    const result = await api.pageSummary({
      page: context.value.id, locale: locale.value,
      facts: Object.fromEntries(facts.value.map(({ key, value }) => [key, value])),
    });
    if (id !== requestId) return;
    if (!result?.summary) throw new Error("Summary unavailable");
    answer.value = result.summary;
    phase.value = "done";
  } catch {
    if (id === requestId) phase.value = "unavailable";
  }
}

function open() {
  dialog.value.showModal();
  summarize();
}
function close() {
  ++requestId;
  if (dialog.value?.open) dialog.value.close();
}
function restoreFocus() {
  if (dialog.value?.open) return;
  ++requestId;
  button.value?.focus();
}
watch(() => route.fullPath, close);
onBeforeUnmount(close);
</script>

<template>
  <button ref="button" class="summary-trigger" type="button" aria-haspopup="dialog" :lang="locale"
          :title="t('Summarize this page with AI', 'ให้ AI สรุปหน้านี้')"
          :aria-label="t('Summarize this page with AI', 'ให้ AI สรุปหน้านี้')" @click="open">
    <UiIcon name="sparkle" :size="18" /><span>{{ t("AI summary", "สรุปด้วย AI") }}</span>
  </button>

  <Teleport to="body">
    <dialog ref="dialog" class="summary-dialog" :lang="locale" aria-labelledby="page-summary-title" @close="restoreFocus" @click.self="close">
      <div class="summary-content">
        <header class="summary-head">
          <span class="summary-mark"><UiIcon name="sparkle" :size="21" /></span>
          <div><p>{{ t("AI summary", "สรุปด้วย AI") }}</p><h2 id="page-summary-title">{{ context.title }}</h2></div>
          <button type="button" class="summary-close" :aria-label="t('Close summary', 'ปิดหน้าสรุป')" autofocus @click="close"><UiIcon name="dismiss" :size="19" /></button>
        </header>

        <p class="muted">{{ context.purpose }}</p>
        <div class="summary-result" role="status">
          <p v-if="phase === 'loading'" class="muted"><UiSpinner :size="16" />{{ t("Preparing your summary…", "กำลังจัดทำสรุป…") }}</p>
          <p v-else-if="phase === 'done'">{{ answer }}</p>
          <p v-else-if="phase === 'unavailable'" class="muted">{{ t("The AI summary is temporarily unavailable.", "ขณะนี้ AI ยังสร้างสรุปไม่ได้") }}</p>
        </div>

        <UiDisclosure v-if="facts.length" class="summary-facts" :open="phase !== 'done' || facts.length < 6"
                      :title="t('What the page reports', 'ข้อมูลที่หน้านี้รายงาน')">
          <ul>
            <li v-for="f in facts" :key="f.key">
              <span>{{ f.label }}</span><b v-if="f.count" class="num">{{ f.value }}</b>
            </li>
          </ul>
        </UiDisclosure>

        <footer>
          <UiButton variant="tint" size="lg" icon="arrow_sync" :disabled="phase === 'loading'" @click="summarize">
            {{ phase === "unavailable" ? t("Try again", "ลองอีกครั้ง") : t("Refresh summary", "อัปเดตสรุป") }}
          </UiButton>
        </footer>
      </div>
    </dialog>
  </Teleport>
</template>

<style scoped>
.summary-trigger { display: inline-flex; align-items: center; justify-content: center; gap: var(--sp-2); min-width: 44px; height: 44px; padding-inline: var(--sp-3); border: 0; border-radius: 14px; background: var(--c-ai-bg); box-shadow: var(--shadow-card); color: var(--c-ai-text); font-size: var(--fs-sm); font-weight: var(--fw-semibold); cursor: pointer; white-space: nowrap; }
.summary-trigger:hover { box-shadow: inset 0 0 0 1px var(--c-ai), var(--shadow-card); }
.summary-trigger:active { background: var(--c-fill-2); }
.summary-dialog { width: min(520px, calc(100% - 32px)); max-height: min(88dvh, 760px); border: 0; padding: 0; border-radius: var(--radius-xl); background: var(--c-surface); color: var(--c-text); box-shadow: var(--shadow-2); overscroll-behavior: contain; }
.summary-dialog::backdrop { background: var(--c-overlay); }
.summary-content { padding: var(--sp-6); }
.summary-head { display: flex; align-items: center; gap: var(--sp-3); margin-bottom: var(--sp-4); }
.summary-head p { font-size: var(--fs-sm); color: var(--c-ai-text); font-weight: var(--fw-semibold); }
.summary-head h2 { font-size: var(--fs-2xl); line-height: var(--lh-snug); }
.summary-mark, .summary-close { width: 44px; height: 44px; flex: none; border-radius: var(--radius-md); display: grid; place-items: center; }
.summary-mark { background: var(--c-ai-bg); color: var(--c-ai-text); }
.summary-close { border: 0; margin-left: auto; background: transparent; color: var(--c-text-2); cursor: pointer; }
.summary-close:hover { background: var(--c-fill); }
.summary-result { margin: var(--sp-4) 0; background: var(--c-fill); border-radius: var(--radius-md); padding: var(--sp-3); overflow-wrap: anywhere; }
.summary-result p { display: flex; align-items: center; gap: var(--sp-2); }
.summary-facts :deep(summary) { min-height: 44px; }
.summary-facts ul { margin: var(--sp-1) 0 0; padding: 0; list-style: none; }
.summary-facts li { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-3); border-bottom: 1px solid var(--c-separator); padding: var(--sp-2) 0; color: var(--c-text-2); }
.summary-facts b { color: var(--c-text); }
footer { display: flex; justify-content: flex-end; margin-top: var(--sp-4); }
@media (min-width: 761px) and (max-width: 1280px) { .summary-trigger span { display: none; } }
@media (max-width: 760px) { .summary-content { padding: var(--sp-4); } }
</style>
