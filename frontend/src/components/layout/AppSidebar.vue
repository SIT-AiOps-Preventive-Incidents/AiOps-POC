<script setup lang="ts">
import NavItem from "./NavItem.vue";
import { useSystemStore } from "@/stores/system";
import { useUiStore } from "@/stores/ui";
const system = useSystemStore();
const ui = useUiStore();
const assetBase = import.meta.env.BASE_URL;
const items = [
  ["/", "Home", "home"],
  ["/problems", "Problems", "problems"],
  ["/map", "Service Map", "service-map"],
  ["/services", "Services", "services"],
  ["/infra", "Computers & Servers", "computers-servers"],
  ["/connect", "Connect", "connect"],
  ["/skills", "Skills & Scores", "skills-scores"],
  ["/runbooks", "Runbooks", "runbooks"],
  ["/notifications", "Notifications", "notifications"],
  ["/deployments", "Deployments", "deployments"],
  ["/chaos", "Demo Scenarios", "demo-scenarios"],
  ["/settings", "Settings", "settings"],
] as const;
</script>
<template>
  <aside class="sidebar" :class="{ open: ui.sidebarOpen }">
    <div class="brand">
      <img
        :src="`${assetBase}icons/aiops-one-mark.svg`"
        width="32"
        height="32"
        alt=""
      />
      <div><strong>AiOps One</strong><span>Incident Intelligence</span></div>
    </div>
    <nav>
      <NavItem
        v-for="item in items"
        :key="item[0]"
        :to="item[0]"
        :label="item[1]"
        :icon="item[2]"
        :badge="item[0] === '/problems' ? system.openProblems : 0"
        @navigate="ui.sidebarOpen = false"
      />
    </nav>
    <div class="sidebar__foot">
      <span :class="{ offline: system.error }">●</span> VM connected · v1.0
    </div>
  </aside>
  <button
    v-if="ui.sidebarOpen"
    class="scrim"
    aria-label="Close menu"
    @click="ui.sidebarOpen = false"
  />
</template>
<style scoped>
.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 40;
  display: flex;
  width: var(--sidebar-width);
  flex-direction: column;
  gap: 12px;
  border-right: 1px solid var(--color-border-default);
  background: white;
  padding: 18px 8px 14px;
}
.brand {
  display: flex;
  height: 44px;
  align-items: center;
  gap: 10px;
  padding-left: 6px;
}
.brand div {
  display: flex;
  flex-direction: column;
  line-height: normal;
}
.brand strong {
  font-size: 12px;
}
.brand span {
  color: var(--color-text-muted);
  font-size: 8px;
}
.sidebar nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sidebar__foot {
  margin-top: auto;
  color: var(--color-text-muted);
  font-size: 8px;
}
.sidebar__foot span {
  color: var(--color-status-success-text);
}
.sidebar__foot span.offline {
  color: var(--color-status-danger-text);
}
.scrim {
  display: none;
}
@media (max-width: 760px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.2s;
  }
  .sidebar.open {
    transform: translateX(0);
  }
  .scrim {
    position: fixed;
    inset: 0;
    z-index: 35;
    display: block;
    border: 0;
    background: rgb(23 32 51 / 30%);
  }
}
</style>
