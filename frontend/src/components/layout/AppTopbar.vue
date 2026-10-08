<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import StatusChip from "@/components/common/StatusChip.vue";
import { useSystemStore } from "@/stores/system";
import { useUiStore } from "@/stores/ui";
const route = useRoute();
const system = useSystemStore();
const ui = useUiStore();
const title = computed(() => String(route.meta.title || "AiOps One"));
const detectorFresh = computed(
  () =>
    !!system.overview?.detector.ts &&
    Date.now() / 1000 - Number(system.overview.detector.ts) < 60,
);
</script>
<template>
  <header class="topbar">
    <div class="title">
      <button aria-label="Open menu" @click="ui.sidebarOpen = true">☰</button
      ><strong>{{ title }}</strong>
    </div>
    <div class="chips">
      <StatusChip :tone="system.overview?.llm.up ? 'success' : 'danger'"
        >LLM
        {{
          system.overview?.llm.up ? system.overview.llm.active : "offline"
        }}</StatusChip
      ><StatusChip :tone="detectorFresh ? 'success' : 'neutral'"
        >Detector {{ detectorFresh ? "live" : "starting"
        }}<template v-if="system.overview?.detector.checks">
          · {{ system.overview.detector.checks }} checks</template
        ></StatusChip
      ><a
        v-if="system.overview?.grafana_url"
        :href="system.overview.grafana_url"
        target="_blank"
        rel="noopener"
        ><StatusChip>Grafana</StatusChip></a
      >
    </div>
  </header>
</template>
<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  height: var(--topbar-height);
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-default);
  background: rgb(255 255 255 / 94%);
  padding: 0 24px;
  backdrop-filter: blur(12px);
}
.title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.title strong {
  font-size: 14px;
}
.title button {
  display: none;
  border: 0;
  background: none;
  font-size: 20px;
}
.chips {
  display: flex;
  align-items: center;
  gap: 8px;
}
@media (max-width: 900px) {
  .chips > :first-child {
    display: none;
  }
}
@media (max-width: 760px) {
  .title button {
    display: block;
  }
  .chips > :not(:last-child) {
    display: none;
  }
  .topbar {
    padding: 0 16px;
  }
}
</style>
