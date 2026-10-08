<script setup>
import { computed } from "vue";
import { useAppStore } from "@/stores/app";
import { useUiStore } from "@/stores/ui";

const app = useAppStore();
const ui = useUiStore();
const NAV = [
  { items: [
    { to: "/", label: "Home", icon: "home" },
    { to: "/problems", label: "Problems", icon: "warning", badge: true },
    { to: "/map", label: "Service Map", icon: "flowchart" },
    { to: "/services", label: "Services", icon: "cube" },
    { to: "/computers", label: "Computers & Servers", icon: "server" },
    { to: "/connect", label: "Connect", icon: "add_circle" },
  ] },
  { label: "AI", items: [
    { to: "/skills", label: "Skills & Scores", icon: "sparkle" },
    { to: "/runbooks", label: "Runbooks", icon: "book" },
    { to: "/notifications", label: "Notifications", icon: "alert" },
  ] },
  { label: "More", items: [
    { to: "/deployments", label: "Deployments", icon: "branch" },
    { to: "/scenarios", label: "Demo Scenarios", icon: "flash" },
    { to: "/design", label: "Design System", icon: "color" },
    { to: "/settings", label: "Settings", icon: "settings" },
  ] },
];
const badge = computed(() => app.kpi.open || 0);
</script>
<template>
  <aside :class="['sidebar', { open: ui.navOpen }]">
    <div class="brand">
      <span class="brand__logo"><UiIcon name="pulse" filled :size="20" /></span>
      <div><b>AIOps One</b><span>Incident intelligence</span></div>
    </div>
    <nav @click="ui.navOpen = false">
      <template v-for="(g, i) in NAV" :key="i">
        <div v-if="g.label" class="nav__sec">{{ g.label }}</div>
        <router-link v-for="it in g.items" :key="it.to" :to="it.to" class="nav__item"
                     :class="{ active: it.to === '/' ? $route.path === '/' : $route.path.startsWith(it.to) }">
          <UiIcon :name="it.icon" :size="20" /><span>{{ it.label }}</span>
          <span v-if="it.badge && badge" class="nav__badge">{{ badge }}</span>
        </router-link>
      </template>
    </nav>
    <footer class="foot">
      <span>{{ app.services.length }} services · {{ app.hosts.length }} computers</span>
      <span class="foot__logos"><UiLogo name="otel" :size="16" alt="OpenTelemetry" /><UiLogo name="prometheus" :size="16" alt="Prometheus" /><UiLogo name="grafana" :size="16" alt="Grafana" />Open source stack</span>
    </footer>
  </aside>
</template>
<style scoped>
.sidebar { width: var(--sidebar-w); flex: none; height: 100vh; display: flex; flex-direction: column; z-index: 30;
  background: rgba(246, 246, 248, 0.92); backdrop-filter: saturate(180%) blur(20px); border-right: 0.5px solid var(--c-separator); }
.brand { display: flex; gap: 10px; align-items: center; padding: 20px 18px 14px; }
.brand__logo { width: 32px; height: 32px; border-radius: 8px; background: var(--c-primary); color: #fff; display: grid; place-items: center; }
.brand b { display: block; font-size: 16px; letter-spacing: -0.02em; }
.brand span { font-size: 12px; color: var(--c-text-2); }
nav { flex: 1; overflow: auto; padding: 4px 10px 10px; }
.nav__sec { font-size: 12px; font-weight: var(--fw-semibold); color: var(--c-text-3); padding: 16px 10px 6px; }
.nav__item { display: flex; align-items: center; gap: 10px; padding: 7px 10px; border-radius: 8px; color: var(--c-text); margin: 1px 0; }
.nav__item .ui-icon { color: var(--c-primary); }
.nav__item:hover { background: rgba(0, 0, 0, 0.04); }
.nav__item.active { background: var(--c-primary); color: #fff; }
.nav__item.active .ui-icon { color: #fff; }
.nav__badge { margin-left: auto; background: var(--c-bad); color: #fff; font-size: 12px; font-weight: var(--fw-semibold); border-radius: 999px; padding: 0 7px; min-width: 20px; text-align: center; }
.nav__item.active .nav__badge { background: #fff; color: var(--c-primary); }
.foot { padding: 12px 18px 16px; font-size: 12px; color: var(--c-text-3); border-top: 0.5px solid var(--c-separator); display: flex; flex-direction: column; gap: 6px; }
.foot__logos { display: flex; align-items: center; gap: 6px; }
@media (max-width: 760px) {
  .sidebar { position: fixed; left: 0; top: 0; transform: translateX(-100%); transition: transform var(--dur) var(--ease); box-shadow: var(--shadow-2); }
  .sidebar.open { transform: none; }
}
</style>
