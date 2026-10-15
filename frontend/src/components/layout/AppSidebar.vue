<script setup>
import { computed } from "vue";
import { useAppStore } from "@/stores/app";
import { useUiStore } from "@/stores/ui";

const app = useAppStore();
const ui = useUiStore();
// Three jobs, in the order an on-call engineer meets them: watch, respond, set up. Two angles on what you run:
// Fleet = the machines (all of them, monitored or not); Service map = the services and how they call each other.
const NAV = [
  { items: [
    { to: "/", label: "Overview", icon: "home" },
    { to: "/problems", label: "Incidents", icon: "warning", badge: true },
    { to: "/network", label: "Fleet", icon: "server" },
    { to: "/map", label: "Service map", icon: "flowchart" },
    { to: "/services", label: "Services", icon: "cube" },
  ] },
  { label: "Automation", items: [
    { to: "/runbooks", label: "Runbooks", icon: "book" },
    { to: "/skills", label: "AI skills", icon: "sparkle" },
  ] },
  { label: "Setup", items: [
    { to: "/connect", label: "Add a host or service", icon: "add_circle" },
    { to: "/notifications", label: "Notifications", icon: "alert" },
    { to: "/settings", label: "Settings", icon: "settings" },
  ] },
  { label: "Demo & tools", items: [
    { to: "/scenarios", label: "Demo scenarios", icon: "flash" },
    { to: "/design", label: "Design system", icon: "sparkle" },
  ] },
];
const badge = computed(() => app.kpi.open || 0);
const waiting = computed(() => app.awaiting.length > 0);
const isActive = (to, path) => (to === "/" ? path === "/" : path.startsWith(to));
</script>
<template>
  <aside :class="['sidebar', { open: ui.navOpen }]">
    <router-link to="/" class="brand" aria-label="AIOps One overview">
      <svg class="brand__mark" viewBox="0 0 28 28" width="28" height="28" aria-hidden="true">
        <rect width="28" height="28" rx="6" fill="var(--c-primary)" />
        <path d="M5 16h4l2.5-6 4 11 2.5-5H23" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        <circle cx="23" cy="16" r="2.6" fill="var(--c-action)" stroke="var(--c-primary)" stroke-width="1" />
      </svg>
      <b>AIOps One</b>
    </router-link>
    <nav @click="ui.navOpen = false">
      <template v-for="(g, i) in NAV" :key="i">
        <div v-if="g.label" class="nav__sec">{{ g.label }}</div>
        <router-link v-for="it in g.items" :key="it.to" :to="it.to" :class="['nav__item', { active: isActive(it.to, $route.path) }]">
          <UiIcon :name="it.icon" :size="18" /><span>{{ it.label }}</span>
          <span v-if="it.badge && badge" :class="['nav__badge', { 'nav__badge--action': waiting }]">{{ badge }}</span>
        </router-link>
      </template>
    </nav>
    <footer class="foot">{{ app.services.length }} services on {{ app.hosts.length }} hosts</footer>
  </aside>
</template>
<style scoped>
.sidebar { width: var(--sidebar-w); flex: none; height: 100vh; display: flex; flex-direction: column; z-index: 30;
  background: var(--c-chrome-side); border-right: 1px solid var(--c-border); }
.brand { display: flex; gap: 10px; align-items: center; height: var(--topbar-h); padding: 0 16px; color: var(--c-text); border-bottom: 1px solid var(--c-border); }
.brand b { font-size: 15px; font-weight: var(--fw-semibold); }
.brand__mark { flex: none; }
nav { flex: 1; overflow: auto; padding: 10px 8px; }
.nav__sec { font-size: var(--fs-xs); font-weight: var(--fw-medium); color: var(--c-text-3); padding: 18px 10px 6px; }
.nav__item { display: flex; align-items: center; gap: 10px; padding: 6px 10px; border-radius: var(--radius-md); color: var(--c-text-2);
  font-weight: var(--fw-medium); margin: 1px 0; position: relative; }
.nav__item .ui-icon { color: var(--c-text-3); }
.nav__item:hover { background: var(--c-fill); color: var(--c-text); }
.nav__item.active { background: var(--c-surface); color: var(--c-text); box-shadow: 0 0 0 1px var(--c-border); }
.nav__item.active::before { content: ""; position: absolute; left: -8px; top: 6px; bottom: 6px; width: 3px; border-radius: 0 2px 2px 0; background: var(--c-primary); }
.nav__item.active .ui-icon { color: var(--c-primary); }
.nav__badge { margin-left: auto; background: var(--c-bad); color: #fff; font-size: var(--fs-xs); font-weight: var(--fw-semibold); border-radius: var(--radius-sm);
  padding: 0 6px; min-width: 20px; line-height: 18px; text-align: center; font-variant-numeric: tabular-nums; }
.nav__badge--action { background: var(--c-action); color: var(--c-on-action); }
.foot { padding: 12px 18px; font-size: var(--fs-xs); color: var(--c-text-3); border-top: 1px solid var(--c-border); }
@media (max-width: 760px) {
  .sidebar { position: fixed; left: 0; top: 0; transform: translateX(-100%); transition: transform var(--dur) var(--ease); box-shadow: var(--shadow-2); }
  .sidebar.open { transform: none; }
}
</style>
