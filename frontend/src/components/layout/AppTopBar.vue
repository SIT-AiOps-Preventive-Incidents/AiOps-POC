<script setup>
import { useAppStore } from "@/stores/app";
import { computed } from "vue";
import { THEMES, useUiStore } from "@/stores/ui";
import { useI18n } from "@/lib/i18n";
const app = useAppStore();
const ui = useUiStore();
const { locale, t, toggle } = useI18n();
const openCmd = () => window.dispatchEvent(new CustomEvent("aiops:command"));
const isMac = typeof navigator !== "undefined" && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent || "");
// one button cycles Auto -> Light -> Dark; the icon shows the current choice
const THEME = { auto: { icon: "dark_theme", label: "Auto (follows your system)" }, light: { icon: "weather_sunny", label: "Light" },
  dark: { icon: "weather_moon", label: "Dark" } };
const mode = computed(() => ui.prefs.theme || "auto");
const nextTheme = () => ui.setTheme(THEMES[(THEMES.indexOf(mode.value) + 1) % THEMES.length]);
</script>
<template>
  <header class="topbar">
    <button class="topbar__menu" aria-label="Open menu" @click="ui.navOpen = !ui.navOpen"><UiIcon name="list" :size="22" /></button>
    <div class="status">
      <span class="status__item" :title="app.detectorLive ? 'The detector checked every service in the last minute' : 'The detector has not reported yet'">
        <span :class="['beat', { live: app.detectorLive }]" />{{ app.detectorLive ? t("Monitoring", "กำลังเฝ้าระวัง") : t("Detector starting", "กำลังเริ่มตัวตรวจจับ") }}</span>
      <span class="status__item"><UiStatusDot :tone="app.llm.up ? 'ok' : 'bad'" :size="7" />AI {{ app.llm.up ? app.llm.active : t("offline", "ออฟไลน์") }}</span>
    </div>
    <button class="search" type="button" @click="openCmd" :aria-label="t('Search', 'ค้นหา')">
      <UiIcon name="search" :size="16" /><span>{{ t("Search incidents, services, hosts…", "ค้นหา incident, บริการ, เครื่อง…") }}</span><kbd>{{ isMac ? "⌘K" : "Ctrl K" }}</kbd>
    </button>
    <div class="tools">
      <UiButton variant="plain" size="sm" :href="app.grafanaUrl"><UiLogo name="grafana" :size="14" />Grafana</UiButton>
      <UiButton variant="plain" size="sm" href="/docs" icon="code">API</UiButton>
      <button class="lang" type="button" :aria-label="t('Switch language', 'สลับภาษา')" :title="t('Language', 'ภาษา')" @click="toggle">
        {{ locale === "th" ? "ไทย" : "EN" }}</button>
      <button class="theme" type="button" :aria-label="`Appearance: ${THEME[mode].label}. Switch appearance`" :title="`Appearance: ${THEME[mode].label}`"
              @click="nextTheme"><UiIcon :name="THEME[mode].icon" :size="18" /></button>
    </div>
  </header>
</template>
<style scoped>
.topbar { height: var(--topbar-h); flex: none; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 24px;
  background: var(--c-chrome-top); border-bottom: 1px solid var(--c-border); z-index: 5; }
.topbar__menu { display: none; background: none; border: 0; color: var(--c-text); padding: 6px; cursor: pointer; }
.status { display: flex; gap: 18px; align-items: center; font-size: var(--fs-sm); color: var(--c-text-2); }
.status__item { display: inline-flex; align-items: center; gap: 7px; white-space: nowrap; }
.beat { width: 7px; height: 7px; border-radius: 50%; background: var(--c-neutral); }
.beat.live { background: var(--c-ok); box-shadow: 0 0 0 0 var(--c-ok); animation: beat 2.4s var(--ease) infinite; }
@keyframes beat { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--c-ok) 55%, transparent); } 70%, 100% { box-shadow: 0 0 0 6px transparent; } }
/* search bar → opens the ⌘K command palette; the one fast way to reach anything */
.search { flex: 1; max-width: 360px; display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 10px; margin: 0 16px;
  border: 1px solid var(--c-border); border-radius: var(--radius-md); background: var(--c-surface); color: var(--c-text-3); cursor: pointer; }
.search:hover { border-color: var(--c-text-3); background: var(--c-fill); }
.search span { flex: 1; min-width: 0; text-align: left; font-size: var(--fs-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.search kbd { font: 500 11px var(--font-mono, monospace); background: var(--c-fill); border: 1px solid var(--c-border); border-radius: 4px; padding: 0 5px; line-height: 16px; color: var(--c-text-2); flex: none; }
.tools { display: flex; gap: 4px; align-items: center; }
.theme, .lang { display: grid; place-items: center; height: 30px; border: 1px solid var(--c-border); border-radius: var(--radius-md);
  background: var(--c-surface); color: var(--c-text-2); cursor: pointer; touch-action: manipulation; }
.theme { width: 30px; margin-left: 6px; }
.lang { min-width: 38px; padding: 0 8px; margin-left: 6px; font: var(--fw-semibold) var(--fs-sm)/1 var(--font); font-variant-numeric: tabular-nums; }
.theme:hover, .lang:hover { background: var(--c-fill); color: var(--c-text); }
@media (max-width: 980px) { .search span, .search kbd { display: none; } .search { flex: none; max-width: none; width: 36px; justify-content: center; padding: 0; margin: 0 8px; } }
@media (max-width: 760px) { .topbar { padding: 0 12px; } .topbar__menu { display: block; } .status__item:last-child { display: none; } }
</style>
