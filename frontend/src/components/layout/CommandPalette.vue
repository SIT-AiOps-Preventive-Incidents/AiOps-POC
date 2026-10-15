<script setup>
// ⌘K / Ctrl+K: jump anywhere, or find an incident, service or host by name - the fast path an on-call
// engineer actually uses instead of hunting through the nav. Open with the shortcut or the top-bar search.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useAppStore } from "@/stores/app";
import { useI18n } from "@/lib/i18n";

const router = useRouter();
const app = useAppStore();
const { t } = useI18n();

const open = ref(false);
const query = ref("");
const sel = ref(0);
const input = ref(null);
const entity = (i) => i.entity_name || i.entity;

function PAGES() {
  return [
    { icon: "home", label: t("Overview", "ภาพรวม"), to: "/" },
    { icon: "warning", label: t("Incidents", "เหตุการณ์"), to: "/problems" },
    { icon: "server", label: t("Fleet", "ฟลีต"), to: "/network" },
    { icon: "flowchart", label: t("Service map", "แผนผังบริการ"), to: "/map" },
    { icon: "cube", label: t("Services", "บริการ"), to: "/services" },
    { icon: "book", label: t("Runbooks", "คู่มือแก้ไข"), to: "/runbooks" },
    { icon: "sparkle", label: t("AI skills", "ทักษะ AI"), to: "/skills" },
    { icon: "add_circle", label: t("Add a host or service", "เพิ่มเครื่องหรือบริการ"), to: "/connect" },
    { icon: "alert", label: t("Notifications", "การแจ้งเตือน"), to: "/notifications" },
    { icon: "settings", label: t("Settings", "การตั้งค่า"), to: "/settings" },
  ];
}

const groups = computed(() => {
  const q = query.value.trim().toLowerCase();
  const has = (...parts) => !q || parts.some((p) => (p || "").toString().toLowerCase().includes(q));
  const out = [];
  const pages = PAGES().filter((p) => has(p.label)).map((p) => ({ ...p, kind: "page" }));
  if (pages.length) out.push({ title: t("Go to", "ไปที่"), items: pages });
  const incs = app.openProblems.filter((i) => has(i.title, entity(i), `p-${i.id}`, `${i.id}`)).slice(0, 6)
    .map((i) => ({ kind: "incident", icon: "warning", label: `P-${i.id} · ${i.title}`, sub: entity(i), to: `/problems/${i.id}` }));
  if (incs.length) out.push({ title: t("Incidents", "เหตุการณ์"), items: incs });
  if (q) {
    const svcs = app.services.filter((s) => has(s.name, s.service)).slice(0, 6)
      .map((s) => ({ kind: "service", icon: "cube", label: s.name, sub: t("Service", "บริการ"), to: `/services/${s.service}` }));
    if (svcs.length) out.push({ title: t("Services", "บริการ"), items: svcs });
    const hosts = app.hosts.filter((h) => has(h.name)).slice(0, 6)
      .map((h) => ({ kind: "host", icon: "server", label: h.name, sub: t("Host", "เครื่อง"), to: `/computers/${h.name}` }));
    if (hosts.length) out.push({ title: t("Hosts", "เครื่อง"), items: hosts });
  }
  return out;
});
const flat = computed(() => groups.value.flatMap((g) => g.items));
watch(flat, () => { if (sel.value >= flat.value.length) sel.value = Math.max(0, flat.value.length - 1); });
watch(query, () => (sel.value = 0));

function show() {
  open.value = true; query.value = ""; sel.value = 0;
  nextTick(() => input.value?.focus());
}
function hide() { open.value = false; }
function go(item) { if (!item) return; hide(); if (item.to) router.push(item.to); }
function move(d) { const n = flat.value.length; if (!n) return; sel.value = (sel.value + d + n) % n; }

function onKey(e) {
  const k = e.key.toLowerCase();
  if ((e.metaKey || e.ctrlKey) && k === "k") { e.preventDefault(); open.value ? hide() : show(); return; }
  if (!open.value) return;
  if (k === "escape") { e.preventDefault(); hide(); }
  else if (k === "arrowdown") { e.preventDefault(); move(1); }
  else if (k === "arrowup") { e.preventDefault(); move(-1); }
  else if (k === "enter") { e.preventDefault(); go(flat.value[sel.value]); }
}
const openEvt = () => show();
onMounted(() => { window.addEventListener("keydown", onKey); window.addEventListener("aiops:command", openEvt); });
onBeforeUnmount(() => { window.removeEventListener("keydown", onKey); window.removeEventListener("aiops:command", openEvt); });

// flat index for a grouped item, so hover/selection line up with keyboard nav
const indexOf = (gi, ii) => { let n = 0; for (let g = 0; g < gi; g++) n += groups.value[g].items.length; return n + ii; };
</script>
<template>
  <teleport to="body">
    <div v-if="open" class="cmd-overlay" @click="hide">
      <div class="cmd" role="dialog" aria-label="Command palette" @click.stop>
        <div class="cmd__search">
          <UiIcon name="search" :size="18" />
          <input ref="input" v-model="query" :placeholder="t('Search incidents, services, hosts, or jump to a page…', 'ค้นหา incident, บริการ, เครื่อง หรือกระโดดไปหน้าใดก็ได้…')"
                 autocomplete="off" spellcheck="false" />
          <kbd>esc</kbd>
        </div>
        <div class="cmd__body">
          <template v-for="(g, gi) in groups" :key="g.title">
            <div class="cmd__grp">{{ g.title }}</div>
            <button v-for="(it, ii) in g.items" :key="it.to + it.label" type="button"
                    :class="['cmd__it', { on: indexOf(gi, ii) === sel }]" @mousemove="sel = indexOf(gi, ii)" @click="go(it)">
              <span class="cmd__ic"><UiIcon :name="it.icon" :size="16" /></span>
              <span class="cmd__l">{{ it.label }}</span>
              <span v-if="it.sub" class="cmd__sub">{{ it.sub }}</span>
            </button>
          </template>
          <div v-if="!flat.length" class="cmd__empty">{{ t("No matches", "ไม่พบ") }}</div>
        </div>
        <div class="cmd__foot"><span><kbd>↑</kbd><kbd>↓</kbd> {{ t("navigate", "เลื่อน") }}</span><span><kbd>↵</kbd> {{ t("open", "เปิด") }}</span><span><kbd>esc</kbd> {{ t("close", "ปิด") }}</span></div>
      </div>
    </div>
  </teleport>
</template>
<style scoped>
.cmd-overlay { position: fixed; inset: 0; z-index: 100; background: var(--c-overlay); backdrop-filter: blur(2px);
  display: flex; align-items: flex-start; justify-content: center; padding: 12vh 16px 16px; }
.cmd { width: 100%; max-width: 580px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-xl);
  box-shadow: var(--shadow-2); overflow: hidden; display: flex; flex-direction: column; max-height: 70vh; }
.cmd__search { display: flex; align-items: center; gap: 10px; padding: 14px 16px; border-bottom: 1px solid var(--c-border); color: var(--c-text-3); }
.cmd__search input { flex: 1; border: 0; background: none; outline: none; font: inherit; font-size: var(--fs-lg); color: var(--c-text); }
.cmd__search input::placeholder { color: var(--c-text-3); }
.cmd__body { overflow: auto; padding: 6px; }
.cmd__grp { font-size: var(--fs-xs); font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text-3); padding: 10px 10px 4px; }
.cmd__it { display: flex; align-items: center; gap: 11px; width: 100%; text-align: left; border: 0; background: none; cursor: pointer;
  padding: 9px 10px; border-radius: var(--radius-md); color: var(--c-text); }
.cmd__it.on { background: var(--c-primary-tint); }
.cmd__ic { width: 28px; height: 28px; border-radius: var(--radius-md); display: grid; place-items: center; flex: none; background: var(--c-fill); color: var(--c-text-2); }
.cmd__it.on .cmd__ic { background: var(--c-surface); color: var(--c-primary); }
.cmd__l { flex: 1; min-width: 0; font-weight: var(--fw-medium); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cmd__sub { font-size: var(--fs-sm); color: var(--c-text-3); flex: none; }
.cmd__empty { padding: 28px; text-align: center; color: var(--c-text-3); }
.cmd__foot { display: flex; gap: 16px; padding: 9px 14px; border-top: 1px solid var(--c-border); font-size: var(--fs-xs); color: var(--c-text-3); }
.cmd__foot span { display: inline-flex; align-items: center; gap: 5px; }
kbd { font: 500 11px var(--font-mono, monospace); background: var(--c-fill); border: 1px solid var(--c-border); border-bottom-width: 2px;
  border-radius: 4px; padding: 0 5px; line-height: 16px; color: var(--c-text-2); }
</style>
