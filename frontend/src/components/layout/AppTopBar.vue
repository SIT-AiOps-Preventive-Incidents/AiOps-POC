<script setup>
// Top-right cluster, as in the reference: search, Guide mode (explanations under page titles on or off), language,
// and the workspace you are looking at. The page title itself sits on the page, left, at the same height.
import { computed } from "vue";
import { useAppStore } from "@/stores/app";
import { useUiStore } from "@/stores/ui";
import { useI18n } from "@/lib/i18n";
const app = useAppStore();
const ui = useUiStore();
const { locale, t, toggle } = useI18n();
const openCmd = () => window.dispatchEvent(new CustomEvent("aiops:command"));
const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || "");
const guide = computed({ get: () => ui.prefs.guide !== false, set: (v) => { ui.setPref("guide", v); document.getElementById("app")?.classList.toggle("guide-off", !v); } });
if (ui.prefs.guide === false) document.getElementById("app")?.classList.add("guide-off");
const host = typeof location !== "undefined" ? location.hostname.split(".")[0].toUpperCase() : "";
</script>
<template>
  <header class="topbar">
    <button class="topbar__menu" aria-label="Open menu" @click="ui.navOpen = !ui.navOpen"><UiIcon name="list" :size="22" /></button>
    <div class="spacer" />
    <button class="search" type="button" @click="openCmd" :aria-label="t('Search', 'ค้นหา')">
      <UiIcon name="search" :size="16" /><span>{{ t("Search", "ค้นหา") }}</span><kbd>{{ isMac ? "⌘K" : "Ctrl K" }}</kbd>
    </button>
    <div class="guide">
      <div class="guide__t"><b>{{ t("Guide mode", "โหมดแนะนำ") }}</b><span>{{ t("Explain what each page shows", "อธิบายว่าแต่ละหน้าแสดงอะไร") }}</span></div>
      <UiSwitch v-model="guide" :label="t('Guide mode', 'โหมดแนะนำ')" />
    </div>
    <button class="lang" type="button" :aria-label="t('Switch language', 'สลับภาษา')" @click="toggle">{{ locale === "th" ? "ไทย" : "EN" }}</button>
    <div class="who">
      <span class="who__av" aria-hidden="true"><UiGlyph name="server" :size="20" /></span>
      <div class="who__t"><span>{{ t("Workspace", "พื้นที่ทำงาน") }}</span><b>{{ host }} · {{ app.hosts.length }} {{ t("hosts", "เครื่อง") }}</b></div>
    </div>
  </header>
</template>
<style scoped>
.topbar { position: absolute; top: 4px; right: 20px; z-index: 6; display: flex; align-items: center; gap: 10px; height: 64px; pointer-events: none; }
.topbar > * { pointer-events: auto; }
.spacer { display: none; }
.topbar__menu { display: none; background: none; border: 0; color: var(--c-text); padding: 6px; cursor: pointer; }
.search { display: flex; align-items: center; gap: 8px; height: 44px; padding: 0 12px 0 14px; border: 0; border-radius: 14px; background: var(--surface);
  box-shadow: var(--shadow-card); color: var(--c-text-3); cursor: pointer; }
.search:hover { color: var(--c-text); }
.search span { font-size: var(--fs-sm); }
.search kbd { font: 500 11px var(--font-mono, monospace); background: var(--c-fill); border-radius: 5px; padding: 1px 6px; color: var(--c-text-2); }
.guide { display: flex; align-items: center; gap: 16px; height: 52px; padding: 0 12px 0 16px; border-radius: 14px; background: var(--surface); box-shadow: var(--shadow-card); }
.guide__t { display: flex; flex-direction: column; line-height: 1.25; } .guide__t b { font-size: var(--fs-sm); } .guide__t span { font-size: 11.5px; color: var(--c-text-3); }
.lang { height: 44px; min-width: 48px; padding: 0 12px; border: 0; border-radius: 14px; background: var(--surface); box-shadow: var(--shadow-card);
  color: var(--c-text-2); cursor: pointer; font: var(--fw-semibold) var(--fs-sm)/1 var(--font); }
.lang:hover { color: var(--c-text); }
.who { display: flex; align-items: center; gap: 10px; padding-left: 6px; }
.who__av { width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; background: var(--c-fill-2); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08); }
.who__t { display: flex; flex-direction: column; line-height: 1.25; } .who__t span { font-size: 11.5px; color: var(--c-text-3); } .who__t b { font-size: var(--fs-sm); white-space: nowrap; }
@media (max-width: 1280px) { .guide__t span, .who__t { display: none; } }
@media (max-width: 980px) { .guide, .who { display: none; } }
@media (max-width: 760px) { .topbar { position: static; right: auto; padding: 0 12px; height: 56px; } .spacer { display: block; flex: 1; } .topbar__menu { display: block; } }
</style>
