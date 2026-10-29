<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useAppStore } from "@/stores/app";
import { THEMES, useUiStore } from "@/stores/ui";
import { useI18n } from "@/lib/i18n";

const app = useAppStore();
const ui = useUiStore();
const route = useRoute();
const { t } = useI18n();
// Watch, respond, set up - in the order an on-call engineer meets them. Fleet and Service map are the two angles on
// what you run (the machines; the services and their calls); Fleet opens into its views as a small tree.
const NAV = computed(() => [
  { label: t("Main", "หลัก"), items: [
    { to: "/", label: t("Overview", "ภาพรวม"), icon: "home" },
    { to: "/problems", label: t("Incidents", "เหตุการณ์"), icon: "warning", badge: true },
    { to: "/network", label: t("Fleet", "ฟลีต"), icon: "server", children: [
      { to: "/network", label: t("Map", "แผนที่"), exact: true },
      { to: "/network/list", label: t("List", "รายการ") },
      { to: "/cloud", label: t("Cloud accounts", "บัญชีคลาวด์") },
      { to: "/network/3d", label: "3D" },
    ] },
    { to: "/map", label: t("Service map", "แผนผังบริการ"), icon: "flowchart" },
    { to: "/services", label: t("Services", "บริการ"), icon: "cube" },
  ] },
  { label: t("Automation", "อัตโนมัติ"), items: [
    { to: "/runbooks", label: t("Runbooks", "คู่มือแก้ไข"), icon: "book" },
    { to: "/skills", label: t("AI skills", "ทักษะ AI"), icon: "sparkle" },
  ] },
  { label: t("Setup", "ตั้งค่า"), items: [
    { to: "/connect", label: t("Connect", "เชื่อมต่อ"), icon: "plug" },
    { to: "/notifications", label: t("Notifications", "การแจ้งเตือน"), icon: "alert" },
    { to: "/settings", label: t("Settings", "การตั้งค่า"), icon: "settings" },
  ] },
  { label: t("Demo & tools", "เดโม่และเครื่องมือ"), items: [
    { to: "/scenarios", label: t("Demo scenarios", "สถานการณ์เดโม่"), icon: "flash" },
    { href: app.grafanaUrl, label: "Grafana", icon: "pulse" },
    { href: "/docs", label: t("API docs", "เอกสาร API"), icon: "book" },
    { to: "/pricing", label: t("Pricing", "ราคา"), icon: "tag" },
    { to: "/design", label: t("Design system", "ดีไซน์ซิสเต็ม"), icon: "color" },
  ] },
]);
const badge = computed(() => app.kpi.open || 0);
const waiting = computed(() => app.awaiting.length);
const isActive = (it) => (it.to === "/" ? route.path === "/" : it.children
  ? it.children.some((c) => route.path.startsWith(c.to)) : route.path.startsWith(it.to));
const childActive = (c) => (c.exact ? route.path === c.to : route.path.startsWith(c.to));
const THEME_LABEL = computed(() => ({ dark: t("Dark", "มืด"), light: t("Light", "สว่าง"), auto: t("Follow system", "ตามระบบ") }));
const theme = computed({ get: () => ui.prefs.theme || "dark", set: (v) => ui.setTheme(v) });
</script>
<template>
  <aside :class="['sidebar', { open: ui.navOpen }]">
    <router-link to="/" class="brand" aria-label="RadarOps overview">
      <UiBrandMark :size="32" />
      <b>RadarOps</b><span class="brand__tag">R2</span>
    </router-link>
    <nav @click="ui.navOpen = false">
      <template v-for="(g, i) in NAV" :key="i">
        <div class="nav__sec">{{ g.label }}</div>
        <template v-for="it in g.items" :key="(it.to || it.href) + it.label">
          <a v-if="it.href" :href="it.href" target="_blank" rel="noopener" class="nav__item">
            <UiGlyph :name="it.icon" :size="20" /><span>{{ it.label }}</span><UiIcon name="chevron_right" :size="13" class="nav__ext" /></a>
          <router-link v-else :to="it.to" :class="['nav__item', { active: isActive(it) }]">
            <UiGlyph :name="it.icon" :size="20" /><span>{{ it.label }}</span>
            <span v-if="it.badge && badge" :class="['nav__badge', { 'nav__badge--action': waiting }]">{{ badge }}</span>
            <UiIcon v-if="it.children" name="chevron_down" :size="14" :class="['nav__caret', { open: isActive(it) }]" />
          </router-link>
          <div v-if="it.children && isActive(it)" class="nav__tree">
            <router-link v-for="c in it.children" :key="c.to" :to="c.to" :class="['nav__leaf', { active: childActive(c) }]">{{ c.label }}</router-link>
          </div>
        </template>
      </template>
    </nav>
    <div class="side-foot">
      <label class="appearance">
        <span class="appearance__k">{{ t("Appearance", "ธีม") }}</span>
        <select v-model="theme" :aria-label="t('Appearance', 'ธีม')">
          <option v-for="m in THEMES" :key="m" :value="m">{{ THEME_LABEL[m] }}</option>
        </select>
        <UiIcon name="chevron_down" :size="14" class="appearance__caret" />
      </label>
      <div class="help">
        <b>{{ waiting ? t(`${waiting} waiting for you`, `รอคุณ ${waiting} รายการ`) : t("Add more to watch", "เพิ่มสิ่งที่ต้องเฝ้าดู") }}</b>
        <span>{{ waiting ? t("A fix is ready. Review it and approve.", "มีวิธีแก้พร้อมแล้ว ตรวจและอนุมัติได้เลย")
          : t(`${app.hosts.length} hosts · ${app.services.length} services watched`, `เฝ้าดู ${app.hosts.length} เครื่อง · ${app.services.length} บริการ`) }}</span>
        <UiButton v-if="waiting" block :to="`/problems/${app.awaiting[0].id}`">{{ t("Review the fix", "ดูวิธีแก้") }}</UiButton>
        <UiButton v-else block to="/connect">{{ t("Connect a server or cloud", "เชื่อมเครื่องหรือคลาวด์") }}</UiButton>
      </div>
    </div>
  </aside>
</template>
<style scoped>
.sidebar { width: var(--sidebar-w); flex: none; height: calc(100vh - 24px); display: flex; flex-direction: column; z-index: 30;
  background: var(--c-chrome-side); border-radius: var(--radius-xl); box-shadow: var(--shadow-card); }
.brand { display: flex; gap: 10px; align-items: center; padding: 22px 22px 14px; color: var(--c-text); }
.brand b { font-size: 19px; font-weight: var(--fw-bold); letter-spacing: -0.02em; }
.brand__tag { font-size: 10px; font-weight: var(--fw-bold); color: var(--c-on-primary); background: var(--grad-primary); padding: 2px 7px; border-radius: var(--radius-pill); }
.brand__mark { flex: none; }
nav { flex: 1; overflow: auto; padding: 4px 12px 12px; }
.nav__sec { font-size: 10.5px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.09em; color: var(--c-text-3); padding: 18px 12px 8px; }
.nav__item { display: flex; align-items: center; gap: 11px; height: 40px; padding: 0 12px; border-radius: 12px; color: var(--c-text-2);
  font-weight: var(--fw-medium); margin: 2px 0; border: 1px solid transparent; }
.nav__item .ui-icon { color: var(--c-text-3); }
.nav__item .ui-glyph { opacity: 0.78; transition: opacity var(--dur-fast) var(--ease); }
.nav__item:hover .ui-glyph, .nav__item.active .ui-glyph { opacity: 1; }
.nav__item:hover { background: var(--c-fill); color: var(--c-text); }
.nav__item.active { background: var(--grad-active); border-color: color-mix(in srgb, var(--c-primary) 42%, transparent); color: var(--c-text); font-weight: var(--fw-semibold);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04); }
.nav__item.active .nav__caret { color: var(--c-text-2); }
.nav__ext { margin-left: auto; color: var(--c-text-3); transform: rotate(-45deg); }
.nav__caret { margin-left: auto; transition: transform var(--dur) var(--ease); transform: rotate(-90deg); }
.nav__caret.open { transform: none; }
.nav__badge { margin-left: auto; background: var(--c-bad); color: #fff; font-size: var(--fs-xs); font-weight: var(--fw-bold); border-radius: var(--radius-pill);
  padding: 0 7px; min-width: 20px; line-height: 19px; text-align: center; font-variant-numeric: tabular-nums; }
.nav__badge--action { background: var(--c-action); color: var(--c-on-action); }
/* the tree: a vertical rule from the parent, a short tick into each leaf */
.nav__tree { margin: 2px 0 6px 21px; padding-left: 14px; border-left: 1px solid var(--c-border); }
.nav__leaf { position: relative; display: block; padding: 7px 10px; font-size: var(--fs-sm); color: var(--c-text-3); border-radius: 8px; }
.nav__leaf::before { content: ""; position: absolute; left: -14px; top: 50%; width: 10px; border-top: 1px solid var(--c-border); }
.nav__leaf:hover { color: var(--c-text); background: var(--c-fill); }
.nav__leaf.active { color: var(--c-text); font-weight: var(--fw-semibold); }
.side-foot { padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.appearance { position: relative; display: flex; flex-direction: column; gap: 2px; padding: 10px 14px; border-radius: 14px; background: var(--c-fill); cursor: pointer; }
.appearance__k { font-size: var(--fs-xs); color: var(--c-text-3); }
.appearance select { appearance: none; background: none; border: 0; padding: 0; font-weight: var(--fw-semibold); cursor: pointer; outline: none; }
.appearance select option { background: var(--surface); color: var(--c-text); }
.appearance__caret { position: absolute; right: 14px; top: 50%; transform: translateY(-50%); color: var(--c-text-3); pointer-events: none; }
.appearance:focus-within { box-shadow: var(--focus-ring); }
.help { display: flex; flex-direction: column; gap: 4px; padding: 16px; border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.025), color-mix(in srgb, var(--c-primary) 9%, transparent));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c-primary) 28%, transparent); }
.help b { font-size: var(--fs-md); } .help span { font-size: var(--fs-sm); color: var(--c-text-3); margin-bottom: 8px; }
@media (max-width: 760px) {
  .sidebar { position: fixed; left: 0; top: 0; height: 100vh; border-radius: 0; transform: translateX(-100%); transition: transform var(--dur) var(--ease); box-shadow: var(--shadow-2); }
  .sidebar.open { transform: none; }
}
</style>
