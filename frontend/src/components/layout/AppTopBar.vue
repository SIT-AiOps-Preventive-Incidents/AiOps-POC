<script setup>
// Top-right cluster, as in the reference: search, Guide mode (explanations under page titles on or off), language,
// and who is signed in (their menu: workspace, role, password, Access, sign out). The page title sits on the page.
import { computed, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import PageSummary from "@/components/layout/PageSummary.vue";
import { api } from "@/lib/api";
import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";
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
const auth = useAuthStore();
const router = useRouter();
const menu = ref(false);
const closeOnOutside = (e) => { if (!e.target.closest?.(".who")) menu.value = false; };
document.addEventListener("click", closeOnOutside);
onBeforeUnmount(() => document.removeEventListener("click", closeOnOutside));
const initials = computed(() => (auth.me?.name || auth.me?.email || "?").split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join(""));
async function signOut() { await auth.logout(); router.replace("/login"); }
// change your own password (people who sign in with a password)
const pw = ref(null);
async function savePassword() {
  try {
    await api.auth.updateMe({ current_password: pw.value.current, password: pw.value.next });
    pw.value = null; ui.toast(t("Password changed", "เปลี่ยนรหัสผ่านแล้ว"));
  } catch (e) { ui.toast(e.message, "bad"); }
}
</script>
<template>
  <header class="topbar">
    <button class="topbar__menu" aria-label="Open menu" @click="ui.navOpen = !ui.navOpen"><UiIcon name="list" :size="22" /></button>
    <div class="spacer" />
    <PageSummary />
    <button class="search" type="button" @click="openCmd" :aria-label="t('Search', 'ค้นหา')">
      <UiIcon name="search" :size="16" /><span class="search__label">{{ t("Search", "ค้นหา") }}</span><kbd>{{ isMac ? "⌘K" : "Ctrl K" }}</kbd>
    </button>
    <div class="guide">
      <div class="guide__t"><b>{{ t("Guide mode", "โหมดแนะนำ") }}</b><span>{{ t("Explain what each page shows", "อธิบายว่าแต่ละหน้าแสดงอะไร") }}</span></div>
      <UiSwitch v-model="guide" :label="t('Guide mode', 'โหมดแนะนำ')" />
    </div>
    <button class="lang" type="button" :aria-label="t('Switch language', 'สลับภาษา')" @click="toggle">{{ locale === "th" ? "ไทย" : "EN" }}</button>
    <div class="who">
      <button type="button" class="who__btn" :aria-expanded="menu" aria-haspopup="menu" @click="menu = !menu">
        <span class="who__av" aria-hidden="true">{{ initials }}</span>
        <div class="who__t"><span>{{ auth.me?.role_label }}</span><b>{{ auth.me?.name || auth.me?.email }}</b></div>
        <UiIcon name="chevron_down" :size="14" />
      </button>
      <div v-if="menu" class="who__menu" role="menu">
        <div class="who__id"><b>{{ auth.me?.name }}</b><span>{{ auth.me?.email }}</span>
          <span>{{ auth.me?.role_label }} · {{ auth.me?.via === "sso" ? t("signed in with SSO", "เข้าผ่าน SSO") : t("signed in with a password", "เข้าด้วยรหัสผ่าน") }}</span></div>
        <div class="who__ws"><UiBrandMark :size="18" /><span>{{ host }} · {{ app.hosts.length }} {{ t("hosts", "เครื่อง") }}</span></div>
        <router-link v-if="auth.can('admin')" to="/access" role="menuitem" class="who__item" @click="menu = false">{{ t("Access and roles", "สิทธิ์และบทบาท") }}</router-link>
        <button v-if="auth.me?.has_password" type="button" role="menuitem" class="who__item" @click="menu = false; pw = { current: '', next: '' }">{{ t("Change password", "เปลี่ยนรหัสผ่าน") }}</button>
        <button type="button" role="menuitem" class="who__item" @click="signOut">{{ t("Sign out", "ออกจากระบบ") }}</button>
      </div>
    </div>
    <UiSheet :model-value="!!pw" :title="t('Change password', 'เปลี่ยนรหัสผ่าน')" :width="420" @update:model-value="pw = null">
      <template v-if="pw">
        <UiField v-model="pw.current" type="password" autocomplete="current-password" :label="t('Current password', 'รหัสผ่านปัจจุบัน')" />
        <UiField v-model="pw.next" type="password" autocomplete="new-password" :label="t('New password', 'รหัสผ่านใหม่')" :hint="t('at least 10 characters', 'อย่างน้อย 10 ตัวอักษร')" />
      </template>
      <template #footer>
        <UiButton variant="ghost" @click="pw = null">{{ t("Cancel", "ยกเลิก") }}</UiButton>
        <UiButton :disabled="!pw?.current || (pw?.next || '').length < 10" @click="savePassword">{{ t("Save", "บันทึก") }}</UiButton>
      </template>
    </UiSheet>
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
.search__label { font-size: var(--fs-sm); }
.search kbd { font: 500 11px var(--font-mono, monospace); background: var(--c-fill); border-radius: 5px; padding: 1px 6px; color: var(--c-text-2); }
.guide { display: flex; align-items: center; gap: 16px; height: 52px; padding: 0 12px 0 16px; border-radius: 14px; background: var(--surface); box-shadow: var(--shadow-card); }
.guide__t { display: flex; flex-direction: column; line-height: 1.25; } .guide__t b { font-size: var(--fs-sm); } .guide__t span { font-size: 11.5px; color: var(--c-text-3); }
.lang { height: 44px; min-width: 48px; padding: 0 12px; border: 0; border-radius: 14px; background: var(--surface); box-shadow: var(--shadow-card);
  color: var(--c-text-2); cursor: pointer; font: var(--fw-semibold) var(--fs-sm)/1 var(--font); }
.lang:hover { color: var(--c-text); }
.who { position: relative; padding-left: 6px; }
.who__btn { display: flex; align-items: center; gap: 10px; background: none; border: 0; color: var(--c-text); cursor: pointer; padding: 4px 6px 4px 0; border-radius: 14px; text-align: left; }
.who__btn .ui-icon { color: var(--c-text-3); }
.who__av { width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; background: var(--c-fill-2); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
  font-size: 13px; font-weight: var(--fw-semibold); color: var(--c-text-2); }
.who__menu { position: absolute; right: 0; top: calc(100% + 8px); width: 260px; background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-2);
  padding: 8px; display: flex; flex-direction: column; z-index: 20; }
.who__id { display: flex; flex-direction: column; gap: 2px; padding: 8px 10px 10px; border-bottom: 1px solid var(--c-separator); }
.who__id span { font-size: 12px; color: var(--c-text-3); overflow-wrap: anywhere; }
.who__ws { display: flex; align-items: center; gap: 8px; padding: 10px; font-size: 12px; color: var(--c-text-3); border-bottom: 1px solid var(--c-separator); margin-bottom: 4px; }
.who__item { display: block; width: 100%; text-align: left; background: none; border: 0; color: var(--c-text); font: inherit; font-size: var(--fs-sm);
  padding: 9px 10px; border-radius: var(--radius-md); cursor: pointer; text-decoration: none; }
.who__item:hover { background: var(--c-fill); }
.who__t { display: flex; flex-direction: column; line-height: 1.25; } .who__t span { font-size: 11.5px; color: var(--c-text-3); } .who__t b { font-size: var(--fs-sm); white-space: nowrap; max-width: 144px; overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 1280px) { .guide__t span, .who__t { display: none; } }
@media (min-width: 761px) and (max-width: 1280px) { .search__label, .search kbd { display: none; } .search { min-width: 44px; padding-inline: 0; justify-content: center; } }
@media (max-width: 980px) { .guide { display: none; } }
@media (max-width: 760px) { .topbar { position: static; right: auto; padding: 0 12px; height: 56px; } .spacer { display: block; flex: 1; } .topbar__menu { display: block; } }
@media (max-width: 480px) { .topbar { gap: 6px; padding-inline: 8px; } .topbar__menu, .search { min-width: 44px; min-height: 44px; } .search { padding-inline: 0; justify-content: center; } .search__label, .search kbd { display: none; } }
</style>
