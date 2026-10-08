<script setup>
import { useAppStore } from "@/stores/app";
import { useUiStore } from "@/stores/ui";
const app = useAppStore();
const ui = useUiStore();
</script>
<template>
  <header class="topbar">
    <button class="topbar__menu" aria-label="Open menu" @click="ui.navOpen = !ui.navOpen"><UiIcon name="list" :size="24" /></button>
    <div class="chips">
      <span class="chip"><UiStatusDot :tone="app.detectorLive ? 'ok' : 'neutral'" />{{ app.detectorLive ? "Monitoring live" : "Detector starting" }}</span>
      <span class="chip"><UiLogo name="ollama" :size="14" alt="Ollama" /><UiStatusDot :tone="app.llm.up ? 'ok' : 'bad'" />{{ app.llm.up ? app.llm.active : "AI offline" }}</span>
    </div>
    <div class="chips">
      <UiButton variant="plain" size="sm" :href="app.grafanaUrl"><UiLogo name="grafana" :size="16" />Grafana</UiButton>
      <UiButton variant="plain" size="sm" href="/docs" icon="code">API</UiButton>
    </div>
  </header>
</template>
<style scoped>
.topbar { height: var(--topbar-h); flex: none; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 0 28px;
  background: rgba(242, 242, 247, 0.85); backdrop-filter: saturate(180%) blur(20px); border-bottom: 0.5px solid var(--c-separator); z-index: 5; }
.topbar__menu { display: none; background: none; border: 0; color: var(--c-primary); padding: 6px; cursor: pointer; }
.chips { display: flex; gap: 8px; align-items: center; }
.chip { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--c-text-2); background: var(--c-surface); border-radius: 999px; padding: 4px 10px; box-shadow: var(--shadow-1); white-space: nowrap; }
@media (max-width: 760px) { .topbar { padding: 0 16px; } .topbar__menu { display: block; } .chips:first-of-type .chip:first-child { display: none; } }
</style>
