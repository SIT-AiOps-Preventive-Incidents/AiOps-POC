<script setup>
import { computed } from "vue";
import { useAppStore } from "@/stores/app";
import { useUiStore } from "@/stores/ui";
import { useI18n } from "@/lib/i18n";

const app = useAppStore();
const ui = useUiStore();
const { t } = useI18n();
// Three jobs, in the order an on-call engineer meets them: watch, respond, set up. Two angles on what you run:
// Fleet = the machines (all of them, monitored or not); Service map = the services and how they call each other.
const NAV = computed(() => [
  { items: [
    { to: "/", label: t("Overview", "ภาพรวม"), icon: "home" },
    { to: "/problems", label: t("Incidents", "เหตุการณ์"), icon: "warning", badge: true },
    { to: "/network", label: t("Fleet", "ฟลีต"), icon: "server" },
    { to: "/map", label: t("Service map", "แผนผังบริการ"), icon: "flowchart" },
    { to: "/services", label: t("Services", "บริการ"), icon: "cube" },
  ] },
  { label: t("Automation", "ระบบอัตโนมัติ"), items: [
    { to: "/runbooks", label: t("Runbooks", "คู่มือแก้ไข"), icon: "book" },
    { to: "/skills", label: t("AI skills", "ทักษะ AI"), icon: "sparkle" },
  ] },
  { label: t("Setup", "ตั้งค่า"), items: [
    { to: "/connect", label: t("Add a host or service", "เพิ่มเครื่องหรือบริการ"), icon: "add_circle" },
    { to: "/notifications", label: t("Notifications", "การแจ้งเตือน"), icon: "alert" },
    { to: "/settings", label: t("Settings", "การตั้งค่า"), icon: "settings" },
  ] },
  { label: t("Demo & tools", "เดโม่และเครื่องมือ"), items: [
    { to: "/scenarios", label: t("Demo scenarios", "สถานการณ์เดโม่"), icon: "flash" },
    { to: "/pricing", label: t("Pricing", "ราคา"), icon: "tag" },
    { to: "/design", label: t("Design system", "ดีไซน์ซิสเต็ม"), icon: "sparkle" },
  ] },
]);
const badge = computed(() => app.kpi.open || 0);
const waiting = computed(() => app.awaiting.length > 0);
const isActive = (to, path) => (to === "/" ? path === "/" : path.startsWith(to));
</script>
<template>
  <aside :class="['sidebar', { open: ui.navOpen }]">
    <router-link to="/" class="brand" aria-label="AIOps One overview">
      <svg class="brand__mark" viewBox="0 0 28 28" width="28" height="28" aria-hidden="true">
        <defs>
          <linearGradient id="bm" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#4f7cff" /><stop offset="1" stop-color="#1b36c8" /></linearGradient>
          <linearGradient id="bmg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#ffffff" stop-opacity="0.18" /><stop offset="0.5" stop-color="#ffffff" stop-opacity="0" /></linearGradient>
        </defs>
        <rect width="28" height="28" rx="8" fill="url(#bm)" />
        <rect width="28" height="28" rx="8" fill="url(#bmg)" />
        <path d="M8 19.5 14 13 20 8" fill="none" stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" opacity="0.95" />
        <circle cx="8" cy="19.5" r="2.4" fill="#fff" />
        <circle cx="14" cy="13" r="2.4" fill="#fff" />
        <circle cx="20" cy="8" r="3" fill="var(--c-action)" stroke="#1b36c8" stroke-width="1.2" />
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
    <footer class="foot">{{ t(`${app.services.length} services on ${app.hosts.length} hosts`, `${app.services.length} บริการบน ${app.hosts.length} เครื่อง`) }}</footer>
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
