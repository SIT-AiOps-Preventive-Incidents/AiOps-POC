<script setup>
/**
 * Access - who can sign in and what each role may do (admins only).
 *   People       add a person with a password, or invite one who signs in with single sign-on; change role, block.
 *   Permissions  the matrix: one row per role, one column per permission grouped like Jenkins' matrix authorization,
 *                a tick in each cell. Admin's row and the Read column stay on. Changes are saved together.
 *   Sign-in      single sign-on (OpenID Connect: Microsoft Entra ID, Google, Keycloak ...), group-to-role rules,
 *                and whether password sign-in stays on.
 *   Activity     sign-ins and every access change, newest first.
 */
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "@/lib/api";
import { groupSpans, matrixChanges, toggleCell } from "@/lib/access";
import { ago } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useAuthStore } from "@/stores/auth";
import { useUiStore } from "@/stores/ui";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();
const auth = useAuthStore();
const { t } = useI18n();
const TABS = computed(() => [{ value: "people", label: t("People", "ผู้ใช้") }, { value: "permissions", label: t("Permissions", "สิทธิ์") },
  { value: "signin", label: t("Sign-in", "การเข้าสู่ระบบ") }, { value: "activity", label: t("Activity", "ประวัติ") }]);
const tab = computed({ get: () => route.query.tab || "permissions", set: (v) => router.replace({ query: { tab: v } }) });

// ---------------- shared ----------------
const roles = ref(null);          // {groups, permissions, roles, matrix, locked}
const edited = ref({});
async function loadRoles() {
  roles.value = await api.roles.get();
  edited.value = JSON.parse(JSON.stringify(roles.value.matrix));
}
loadRoles();
const roleLabel = (id) => roles.value?.roles.find((r) => r.id === id)?.label || id;
const permLabel = (id) => roles.value?.permissions.find((p) => p.id === id)?.label || id;

// ---------------- permissions matrix ----------------
const spans = computed(() => (roles.value ? groupSpans(roles.value.permissions, roles.value.groups) : []));
const changes = computed(() => (roles.value ? matrixChanges(roles.value.matrix, edited.value) : []));
const ticked = (role, perm) => role === "admin" || (edited.value[role] || []).includes(perm) || (edited.value[role] || []).includes("admin");
const locked = (role, perm) => role === "admin" || perm === "read" || (perm !== "admin" && (edited.value[role] || []).includes("admin"));
const firstOfGroup = (i) => i === 0 || roles.value.permissions[i - 1].group !== roles.value.permissions[i].group;
function flip(role, perm) { if (!locked(role, perm)) edited.value = toggleCell(edited.value, role, perm); }
const hoverCol = ref(null);
const saving = ref(false);
async function saveMatrix() {
  saving.value = true;
  try {
    roles.value = await api.roles.saveMatrix(edited.value);
    edited.value = JSON.parse(JSON.stringify(roles.value.matrix));
    ui.toast(t("Permissions saved. They apply from the next click.", "บันทึกสิทธิ์แล้ว มีผลตั้งแต่คลิกถัดไป"));
    auth.load();
  } catch (e) { ui.toast(e.message, "bad"); } finally { saving.value = false; }
}
const discard = () => (edited.value = JSON.parse(JSON.stringify(roles.value.matrix)));
const changeLine = (c) => [c.added.length ? `+ ${c.added.map(permLabel).join(", ")}` : "", c.removed.length ? `− ${c.removed.map(permLabel).join(", ")}` : ""].filter(Boolean).join("  ");

// add / rename / remove a role
const roleSheet = ref(null);      // null · {} new · a role
const roleForm = ref({ label: "", copy_from: "viewer" });
const openRole = (r = {}) => { roleSheet.value = r; roleForm.value = { label: r.label || "", copy_from: "viewer" }; };
async function saveRole() {
  try {
    if (roleSheet.value.id) await api.roles.rename(roleSheet.value.id, roleForm.value.label);
    else await api.roles.create(roleForm.value);
    roleSheet.value = null; await loadRoles();
  } catch (e) { ui.toast(e.message, "bad"); }
}
async function removeRole(r) {
  try { await api.roles.remove(r.id); roleSheet.value = null; await loadRoles(); } catch (e) { ui.toast(e.message, "bad"); }
}

// ---------------- people ----------------
const people = ref(null);
const loadPeople = async () => { people.value = await api.users.list(); };
watch(tab, (v) => { if (v === "people" && !people.value) loadPeople(); if (v === "activity") loadLog(); if (v === "signin" && !sso.value) loadSso(); }, { immediate: true });
async function patchUser(u, b) {
  try { await api.users.update(u.id, b); await loadPeople(); } catch (e) { ui.toast(e.message, "bad"); await loadPeople(); }
}
const personSheet = ref(null);
const personForm = ref({});
const openPerson = (u = {}) => { personSheet.value = u; personForm.value = { email: u.email || "", name: u.name || "", role: u.role || "viewer", withPassword: !u.id, password: "" }; };
async function savePerson() {
  const f = personForm.value;
  try {
    if (personSheet.value.id) await api.users.update(personSheet.value.id, { name: f.name, role: f.role, ...(f.password ? { password: f.password } : {}) });
    else await api.users.create({ email: f.email, name: f.name, role: f.role, ...(f.withPassword ? { password: f.password } : {}) });
    personSheet.value = null; await loadPeople(); await loadRoles();
  } catch (e) { ui.toast(e.message, "bad"); }
}
const armed = ref(null);
async function removePerson(u) {
  if (armed.value !== u.id) { armed.value = u.id; setTimeout(() => { if (armed.value === u.id) armed.value = null; }, 4000); return; }
  armed.value = null;
  try { await api.users.remove(u.id); personSheet.value = null; await loadPeople(); await loadRoles(); } catch (e) { ui.toast(e.message, "bad"); }
}

// ---------------- sign-in ----------------
const sso = ref(null);
const ssoForm = ref({});
async function loadSso() {
  sso.value = await api.auth.sso.get();
  ssoForm.value = { ...sso.value, sso_client_secret: "", sso_role_rules: (sso.value.sso_role_rules || []).map((r) => ({ ...r })) };
}
const testing = ref(false);
async function testSso() {
  testing.value = true;
  try { const r = await api.auth.sso.test({ sso_issuer: ssoForm.value.sso_issuer }); ui.toast(t(`Provider answered: ${r.issuer}`, `ผู้ให้บริการตอบกลับแล้ว: ${r.issuer}`)); }
  catch (e) { ui.toast(e.message, "bad"); } finally { testing.value = false; }
}
async function saveSso() {
  const f = ssoForm.value;
  const body = { sso_enabled: f.sso_enabled, sso_label: f.sso_label, sso_issuer: f.sso_issuer.trim(), sso_client_id: f.sso_client_id.trim(),
    sso_default_role: f.sso_default_role, sso_allowed_domains: f.sso_allowed_domains, password_login: f.password_login,
    sso_role_rules: f.sso_role_rules.filter((r) => r.value.trim()) };
  if (f.sso_client_secret) body.sso_client_secret = f.sso_client_secret;
  try { await api.auth.sso.update(body); ui.toast(t("Sign-in settings saved", "บันทึกการตั้งค่าการเข้าสู่ระบบแล้ว")); await loadSso(); }
  catch (e) { ui.toast(e.message, "bad"); }
}
const addRule = () => ssoForm.value.sso_role_rules.push({ claim: "groups", value: "", role: "developer" });
const copy = (s) => navigator.clipboard?.writeText(s).then(() => ui.toast(t("Copied", "คัดลอกแล้ว")));

// ---------------- activity ----------------
const log = ref(null);
const loadLog = async () => { log.value = await api.auth.log(); };
const ACTION = { login: "Signed in", "login.fail": "Sign-in failed", logout: "Signed out", "matrix.change": "Changed permissions",
  "role.create": "Added a role", "role.rename": "Renamed a role", "role.delete": "Removed a role", "user.create": "Added a person",
  "user.update": "Changed a person", "user.delete": "Removed a person", "user.sso_join": "Joined through SSO",
  "user.sso_link": "Linked SSO to an account", "user.sso_role": "Role set by an SSO rule", "sso.change": "Changed sign-in settings",
  "user.bootstrap": "First admin created" };
function detail(e) {
  const d = e.detail || {};
  if (e.action === "matrix.change") return Object.entries(d).map(([r, c]) => `${roleLabel(r)}: ${changeLine(c)}`).join(" · ");
  if (e.action.startsWith("login")) return [d.via, d.ip, d.reason].filter(Boolean).join(" · ");
  return Object.entries(d).map(([k, v]) => `${k} ${typeof v === "object" ? JSON.stringify(v) : v}`).join(" · ");
}
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader :eyebrow="t('Setup', 'ตั้งค่า')" :title="t('Access', 'สิทธิ์การเข้าถึง')"
                  :subtitle="t('Who can sign in, and what each role may do.', 'ใครเข้าระบบได้ และแต่ละบทบาททำอะไรได้บ้าง')">
      <UiButton v-if="tab === 'people'" icon="add" @click="openPerson()">{{ t("Add person", "เพิ่มผู้ใช้") }}</UiButton>
      <UiButton v-else-if="tab === 'permissions'" icon="add" variant="tint" @click="openRole()">{{ t("Add role", "เพิ่มบทบาท") }}</UiButton>
    </UiPageHeader>
    <div class="tabs"><UiSegmented v-model="tab" :options="TABS" :label="t('Section', 'หมวด')" /></div>

    <!-- ===== permissions matrix ===== -->
    <section v-if="tab === 'permissions'">
      <UiSkeletonPage v-if="!roles" />
      <div v-else class="card matrix-card">
        <div class="matrix-scroll">
          <table class="matrix" @mouseleave="hoverCol = null">
            <thead>
              <tr class="groups">
                <th class="rolecol" rowspan="2">{{ t("Role", "บทบาท") }}</th>
                <th v-for="g in spans" :key="g.group" :colspan="g.span" class="g">{{ g.group }}</th>
              </tr>
              <tr class="perms">
                <th v-for="(p, i) in roles.permissions" :key="p.id" :title="p.help" :class="{ sep: firstOfGroup(i), hot: hoverCol === p.id }">
                  <span>{{ p.label }}</span></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in roles.roles" :key="r.id">
                <th class="rolecol" scope="row">
                  <div class="rname">
                    <span><b>{{ r.label }}</b><small>{{ r.users }} {{ r.users === 1 ? t("person", "คน") : t("people", "คน") }}</small></span>
                    <button v-if="!r.builtin" type="button" class="link" @click="openRole(r)">{{ t("Edit", "แก้ไข") }}</button>
                  </div>
                </th>
                <td v-for="(p, i) in roles.permissions" :key="p.id" :class="{ sep: firstOfGroup(i), hot: hoverCol === p.id }" @mouseenter="hoverCol = p.id">
                  <label class="cell" :title="`${r.label} · ${p.label}: ${p.help}`">
                    <input type="checkbox" :checked="ticked(r.id, p.id)" :disabled="locked(r.id, p.id)"
                           :aria-label="`${r.label} ${p.label}`" @change="flip(r.id, p.id)">
                  </label>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="note">{{ t("Admin's row and the Read column always stay on. Hover a column name for what it allows.", "แถวของ Admin และคอลัมน์ Read เปิดไว้เสมอ ชี้ที่ชื่อคอลัมน์เพื่อดูว่าสิทธิ์นั้นทำอะไรได้") }}</p>
      </div>
      <div v-if="changes.length" class="changebar" role="status">
        <div class="changes">
          <b>{{ changes.length }} {{ t("role(s) changed", "บทบาทที่เปลี่ยน") }}</b>
          <span v-for="c in changes" :key="c.role">{{ roleLabel(c.role) }}: {{ changeLine(c) }}</span>
        </div>
        <div class="row"><UiButton variant="ghost" @click="discard">{{ t("Discard", "ยกเลิก") }}</UiButton>
          <UiButton :loading="saving" @click="saveMatrix">{{ t("Save permissions", "บันทึกสิทธิ์") }}</UiButton></div>
      </div>
    </section>

    <!-- ===== people ===== -->
    <section v-else-if="tab === 'people'">
      <UiSkeletonPage v-if="!people" />
      <div v-else class="card">
        <div class="people">
          <div class="tr th"><span>{{ t("Person", "ผู้ใช้") }}</span><span>{{ t("Role", "บทบาท") }}</span><span>{{ t("Signs in with", "เข้าระบบด้วย") }}</span>
            <span>{{ t("Last sign-in", "เข้าล่าสุด") }}</span><span>{{ t("Active", "ใช้งาน") }}</span><span /></div>
          <div v-for="u in people" :key="u.id" :class="['tr', { off: !u.active }]">
            <span class="who"><b>{{ u.name || u.email }}</b><small>{{ u.email }}<template v-if="u.id === auth.me?.id"> · {{ t("you", "คุณ") }}</template></small></span>
            <span><select class="sel" :value="u.role" :aria-label="t('Role', 'บทบาท')" @change="patchUser(u, { role: $event.target.value })">
              <option v-for="r in roles?.roles || []" :key="r.id" :value="r.id">{{ r.label }}</option></select></span>
            <span class="muted">{{ [u.sso ? "SSO" : "", u.has_password ? t("Password", "รหัสผ่าน") : ""].filter(Boolean).join(" + ") || t("SSO (invited)", "SSO (เชิญไว้)") }}</span>
            <span class="muted">{{ u.last_login_at ? ago(u.last_login_at) : t("Never", "ยังไม่เคย") }}</span>
            <span><UiSwitch :model-value="u.active" :label="`${t('Active', 'ใช้งาน')} ${u.email}`" @update:model-value="(v) => patchUser(u, { active: v })" /></span>
            <span class="act"><UiButton size="sm" variant="ghost" @click="openPerson(u)">{{ t("Edit", "แก้ไข") }}</UiButton></span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== sign-in ===== -->
    <section v-else-if="tab === 'signin'">
      <UiSkeletonPage v-if="!sso" />
      <div v-else class="signin">
        <div class="card">
          <div class="head"><h3>{{ t("Single sign-on", "Single sign-on") }}</h3><UiSwitch v-model="ssoForm.sso_enabled" :label="t('Use single sign-on', 'ใช้ single sign-on')" /></div>
          <p class="sub">{{ t("OpenID Connect: Microsoft Entra ID, Google Workspace, Keycloak, Okta, Dex ... Register RadarOps there with the redirect URL below.",
                              "OpenID Connect: Microsoft Entra ID, Google Workspace, Keycloak, Okta, Dex ... ลงทะเบียน RadarOps ที่ผู้ให้บริการด้วย redirect URL ด้านล่าง") }}</p>
          <div class="redirect"><span class="mono small">{{ sso.redirect_uri }}</span><UiButton size="sm" variant="ghost" icon="copy" @click="copy(sso.redirect_uri)">{{ t("Copy", "คัดลอก") }}</UiButton></div>
          <div class="two">
            <UiField v-model="ssoForm.sso_issuer" mono :label="t('Issuer URL', 'Issuer URL')" placeholder="https://login.microsoftonline.com/<tenant>/v2.0" />
            <div class="testbtn"><UiButton variant="tint" :loading="testing" :disabled="!ssoForm.sso_issuer" @click="testSso">{{ t("Test", "ทดสอบ") }}</UiButton></div>
          </div>
          <div class="two">
            <UiField v-model="ssoForm.sso_client_id" mono :label="t('Client ID', 'Client ID')" />
            <UiField v-model="ssoForm.sso_client_secret" type="password" mono :label="t('Client secret', 'Client secret')"
                     :placeholder="sso.has_secret ? t('Saved. Leave blank to keep it.', 'บันทึกไว้แล้ว เว้นว่างเพื่อใช้ค่าเดิม') : ''" />
          </div>
          <div class="two">
            <UiField v-model="ssoForm.sso_label" :label="t('Button text', 'ข้อความบนปุ่ม')" placeholder="Sign in with Microsoft" />
            <UiField v-model="ssoForm.sso_allowed_domains" :label="t('Allowed email domains', 'โดเมนอีเมลที่อนุญาต')" :hint="t('optional, comma separated', 'ไม่บังคับ คั่นด้วยจุลภาค')" placeholder="kmutt.ac.th, b3tech.co.th" />
          </div>
        </div>

        <div class="card">
          <h3>{{ t("Roles from the provider", "บทบาทจากผู้ให้บริการ") }}</h3>
          <p class="sub">{{ t("Checked at every sign-in, top to bottom; the first rule that matches sets the role. No match: a new person gets the default role and an existing one keeps theirs.",
                              "เช็คทุกครั้งที่เข้าระบบ จากบนลงล่าง กฎแรกที่ตรงจะกำหนดบทบาท ถ้าไม่ตรงเลย คนใหม่ได้บทบาทเริ่มต้น คนเดิมได้บทบาทเดิม") }}</p>
          <div v-for="(r, i) in ssoForm.sso_role_rules" :key="i" class="rule">
            <select v-model="r.claim" class="sel" :aria-label="t('Claim', 'Claim')"><option value="groups">groups</option><option value="roles">roles</option><option value="email">email</option></select>
            <span class="muted">{{ t("contains", "มีค่า") }}</span>
            <input v-model="r.value" class="inp mono" :placeholder="r.claim === 'email' ? 'name@company.com' : 'radarops-admins'" :aria-label="t('Value', 'ค่า')">
            <span class="muted">→</span>
            <select v-model="r.role" class="sel" :aria-label="t('Role', 'บทบาท')"><option v-for="ro in roles?.roles || []" :key="ro.id" :value="ro.id">{{ ro.label }}</option></select>
            <UiButton size="sm" variant="ghost" icon="dismiss" :aria-label="t('Remove rule', 'ลบกฎ')" @click="ssoForm.sso_role_rules.splice(i, 1)" />
          </div>
          <UiButton size="sm" variant="tint" icon="add" @click="addRule">{{ t("Add rule", "เพิ่มกฎ") }}</UiButton>
          <label class="sel-row"><span>{{ t("Default role for new people", "บทบาทเริ่มต้นของคนใหม่") }}</span>
            <select v-model="ssoForm.sso_default_role" class="sel"><option v-for="ro in roles?.roles || []" :key="ro.id" :value="ro.id">{{ ro.label }}</option></select></label>
        </div>

        <div class="card">
          <div class="head"><div><h3>{{ t("Password sign-in", "เข้าระบบด้วยรหัสผ่าน") }}</h3>
            <p class="sub">{{ t("Can be switched off once single sign-on works and an admin has signed in with it.", "ปิดได้เมื่อ single sign-on ใช้งานได้ และมี admin เข้าระบบผ่าน SSO แล้ว") }}</p></div>
            <UiSwitch v-model="ssoForm.password_login" :label="t('Password sign-in', 'เข้าระบบด้วยรหัสผ่าน')" /></div>
        </div>
        <div class="save"><UiButton @click="saveSso">{{ t("Save sign-in settings", "บันทึกการตั้งค่า") }}</UiButton></div>
      </div>
    </section>

    <!-- ===== activity ===== -->
    <section v-else-if="tab === 'activity'">
      <UiSkeletonPage v-if="!log" />
      <div v-else class="card">
        <div v-for="e in log" :key="e.id" class="ev">
          <span class="when muted small">{{ ago(e.ts) }}</span>
          <span><b>{{ ACTION[e.action] || e.action }}</b><small class="muted"> {{ e.actor }}</small></span>
          <span class="muted small">{{ detail(e) }}</span>
        </div>
        <p v-if="!log.length" class="muted">{{ t("Nothing yet.", "ยังไม่มีรายการ") }}</p>
      </div>
    </section>

    <!-- role sheet -->
    <UiSheet :model-value="!!roleSheet" :title="roleSheet?.id ? t('Edit role', 'แก้ไขบทบาท') : t('Add role', 'เพิ่มบทบาท')" @update:model-value="roleSheet = null">
      <template v-if="roleSheet">
        <UiField v-model="roleForm.label" :label="t('Name', 'ชื่อ')" placeholder="On-call SRE" />
        <label v-if="!roleSheet.id" class="sel-row"><span>{{ t("Start from the ticks of", "เริ่มจากสิทธิ์ของ") }}</span>
          <select v-model="roleForm.copy_from" class="sel"><option v-for="r in roles?.roles || []" :key="r.id" :value="r.id">{{ r.label }}</option></select></label>
      </template>
      <template #footer>
        <UiButton v-if="roleSheet?.id" variant="ghost" :disabled="roleSheet.users > 0" @click="removeRole(roleSheet)">{{ t("Remove role", "ลบบทบาท") }}</UiButton>
        <span class="grow" />
        <UiButton variant="ghost" @click="roleSheet = null">{{ t("Cancel", "ยกเลิก") }}</UiButton>
        <UiButton :disabled="!roleForm.label.trim()" @click="saveRole">{{ t("Save", "บันทึก") }}</UiButton>
      </template>
    </UiSheet>

    <!-- person sheet -->
    <UiSheet :model-value="!!personSheet" :title="personSheet?.id ? personSheet.email : t('Add person', 'เพิ่มผู้ใช้')" @update:model-value="personSheet = null">
      <template v-if="personSheet">
        <UiField v-if="!personSheet.id" v-model="personForm.email" type="email" :label="t('Email', 'อีเมล')" placeholder="name@company.com" />
        <UiField v-model="personForm.name" :label="t('Name', 'ชื่อ')" />
        <label class="sel-row"><span>{{ t("Role", "บทบาท") }}</span>
          <select v-model="personForm.role" class="sel"><option v-for="r in roles?.roles || []" :key="r.id" :value="r.id">{{ r.label }}</option></select></label>
        <label v-if="!personSheet.id" class="sel-row"><span>{{ t("Give a password now", "ตั้งรหัสผ่านให้เลย") }}</span><UiSwitch v-model="personForm.withPassword" :label="t('Give a password now', 'ตั้งรหัสผ่านให้เลย')" /></label>
        <UiField v-if="personSheet.id || personForm.withPassword" v-model="personForm.password" type="password"
                 :label="personSheet.id ? t('New password', 'รหัสผ่านใหม่') : t('Password', 'รหัสผ่าน')"
                 :hint="personSheet.id ? t('leave blank to keep', 'เว้นว่างเพื่อใช้ค่าเดิม') : t('at least 10 characters', 'อย่างน้อย 10 ตัวอักษร')" />
        <p v-if="!personSheet.id && !personForm.withPassword" class="sub">{{ t("They sign in with single sign-on using this email; their account links on first sign-in.", "ผู้ใช้จะเข้าระบบผ่าน SSO ด้วยอีเมลนี้ บัญชีจะเชื่อมกันตอนเข้าครั้งแรก") }}</p>
      </template>
      <template #footer>
        <UiButton v-if="personSheet?.id && personSheet.id !== auth.me?.id" :variant="armed === personSheet.id ? 'danger' : 'ghost'" @click="removePerson(personSheet)">
          {{ armed === personSheet.id ? t("Click to confirm", "คลิกอีกครั้งเพื่อยืนยัน") : t("Remove", "ลบ") }}</UiButton>
        <span class="grow" />
        <UiButton variant="ghost" @click="personSheet = null">{{ t("Cancel", "ยกเลิก") }}</UiButton>
        <UiButton :disabled="!personSheet?.id && !personForm.email" @click="savePerson">{{ t("Save", "บันทึก") }}</UiButton>
      </template>
    </UiSheet>
  </div>
</template>
<style scoped>
.tabs { margin-bottom: 16px; }
.card { background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 20px 22px; margin-bottom: 14px; }
.card h3 { font-size: 16px; font-weight: var(--fw-semibold); }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 4px; }
.head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.grow { flex: 1; }

/* matrix */
.matrix-card { padding: 0; overflow: hidden; }
.matrix-scroll { overflow-x: auto; }
.matrix { border-collapse: separate; border-spacing: 0; width: 100%; font-size: var(--fs-sm); }
.matrix th, .matrix td { border-bottom: 1px solid var(--c-border); }
.matrix .rolecol { position: sticky; left: 0; z-index: 1; background: var(--surface); text-align: left; min-width: 180px; padding: 10px 16px;
  border-right: 1px solid var(--c-border); }
.matrix thead .rolecol { vertical-align: bottom; color: var(--c-text-3); font-weight: var(--fw-medium); }
.groups .g { font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-text-3); font-weight: var(--fw-semibold);
  padding: 10px 8px 6px; text-align: center; border-left: 1px solid var(--c-border); }
.perms th { padding: 6px 4px 10px; font-weight: var(--fw-medium); color: var(--c-text-2); vertical-align: bottom; min-width: 76px; cursor: help; }
.perms th span { display: block; line-height: 1.25; }
.matrix .sep { border-left: 1px solid var(--c-border); }
.matrix td { text-align: center; padding: 0; }
.matrix .hot { background: color-mix(in srgb, var(--c-primary) 7%, transparent); }
.matrix tbody tr:hover td, .matrix tbody tr:hover .rolecol { background: color-mix(in srgb, var(--c-primary) 7%, var(--surface)); }
.cell { display: flex; align-items: center; justify-content: center; height: 44px; cursor: pointer; }
.cell input { width: 17px; height: 17px; accent-color: var(--c-primary); cursor: pointer; }
.cell input:disabled { cursor: not-allowed; opacity: 0.55; }
.rname { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.rname small { display: block; color: var(--c-text-3); font-weight: var(--fw-regular); font-size: 12px; }
.link { background: none; border: 0; color: var(--c-primary); cursor: pointer; font-size: 12px; padding: 0; }
.note { font-size: 12px; color: var(--c-text-3); padding: 10px 16px; }
.changebar { position: sticky; bottom: 16px; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap;
  background: var(--surface); border: 1px solid color-mix(in srgb, var(--c-primary) 45%, transparent); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-2); padding: 12px 16px; margin-top: 12px; }
.changes { display: flex; flex-direction: column; gap: 2px; font-size: var(--fs-sm); color: var(--c-text-2); }

/* people */
.people .tr { display: grid; grid-template-columns: minmax(200px, 2fr) 160px 140px 120px 70px 80px; gap: 12px; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--c-border); }
.people .th { font-size: 12px; color: var(--c-text-3); font-weight: var(--fw-medium); padding-top: 0; }
.people .tr:last-child { border-bottom: 0; }
.people .off { opacity: 0.55; }
.who small { display: block; color: var(--c-text-3); font-size: 12px; }
.act { text-align: right; }
.sel, .inp { background: var(--c-fill); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 7px 10px; font-size: var(--fs-sm); color: var(--c-text); }
.sel:focus, .inp:focus { outline: none; border-color: var(--c-primary); box-shadow: 0 0 0 3px var(--c-primary-tint); }
.sel-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 16px; font-size: var(--fs-sm); color: var(--c-text-2); }

/* sign-in */
.redirect { display: flex; align-items: center; justify-content: space-between; gap: 8px; background: var(--c-fill); border-radius: var(--radius-md);
  padding: 6px 6px 6px 12px; margin-top: 14px; overflow-wrap: anywhere; }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: end; }
.testbtn { padding-bottom: 2px; }
.rule { display: grid; grid-template-columns: 110px auto 1fr auto 150px auto; gap: 8px; align-items: center; margin: 10px 0; }
.save { display: flex; justify-content: flex-end; }

/* activity */
.ev { display: grid; grid-template-columns: 110px 260px 1fr; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--c-border); align-items: baseline; }
.ev:last-child { border-bottom: 0; }

@media (max-width: 760px) {
  .people .tr { grid-template-columns: 1fr auto; }
  .people .th { display: none; }
  .two, .rule, .ev { grid-template-columns: 1fr; }
}
</style>
