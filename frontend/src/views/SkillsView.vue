<script setup>
/**
 * AI skills - what the AI investigates, and with which read-only tools. Built-in skills come with RadarOps; a team can
 * switch them off or give them instructions in its own words. A team's own skill rides on the built-in investigation
 * for the same incident kind and adds its tools and instructions on top. Skill sets say which skills investigate which
 * part of the estate (pay-*, checkout ...).
 */
import { computed, ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { kindLabel, skillBody, skillForm, toggle } from "@/lib/automation";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const skills = ref(null);
const sets = ref([]);
const catalog = ref({ tools: {}, kinds: [] });
const { refresh } = usePolling(async () => { [skills.value, sets.value] = await Promise.all([api.skills.list(), api.skillSets.list()]); }, 30000);
api.automation.catalog().then((c) => (catalog.value = c));
const yours = computed(() => (skills.value || []).filter((s) => !s.builtin));
const builtin = computed(() => (skills.value || []).filter((s) => s.builtin));
const nameOf = (id) => (skills.value || []).find((s) => s.id === id)?.name || id;

// ---- skill sheet ----
const editing = ref(null);          // null closed · {} new · a skill
const form = ref(skillForm());
const err = ref("");
const busy = ref(false);
const open = (s = {}) => { editing.value = s; form.value = skillForm(s); err.value = ""; };
const isBuiltin = computed(() => !!editing.value?.builtin);
async function save() {
  busy.value = true; err.value = "";
  try {
    if (isBuiltin.value) await api.skills.update(editing.value.id, { enabled: form.value.enabled, instructions: form.value.instructions.trim() });
    else if (editing.value.id) await api.skills.update(editing.value.id, skillBody(form.value));
    else await api.skills.create(skillBody(form.value));
    ui.toast(`Saved ${form.value.name}`); editing.value = null; refresh();
  } catch (e) { err.value = e.message; } finally { busy.value = false; }
}
async function setEnabled(s, on) {
  await api.skills.update(s.id, s.builtin ? { enabled: on, instructions: s.instructions || "" } : { enabled: on }); refresh();
}
// delete is two clicks: the first arms the button
const armed = ref(null);
async function remove(kind, item) {
  const key = `${kind}:${item.id}`;
  if (armed.value !== key) { armed.value = key; setTimeout(() => { if (armed.value === key) armed.value = null; }, 4000); return; }
  armed.value = null;
  await (kind === "skill" ? api.skills.remove(item.id) : api.skillSets.remove(item.id));
  ui.toast(`Deleted ${item.name}`); editing.value = null; setEditing.value = null; refresh();
}

// ---- skill set sheet ----
const setEditing = ref(null);
const setForm = ref({ name: "", scope: "", skills: [], enabled: true });
const openSet = (s = {}) => { setEditing.value = s; setForm.value = { name: s.name || "", scope: s.scope || "", skills: [...(s.skills || [])], enabled: s.enabled ?? true }; err.value = ""; };
async function saveSet() {
  busy.value = true; err.value = "";
  const body = { ...setForm.value, name: setForm.value.name.trim(), scope: setForm.value.scope.trim() };
  try {
    await (setEditing.value.id ? api.skillSets.update(setEditing.value.id, body) : api.skillSets.create(body));
    ui.toast(`Saved ${body.name}`); setEditing.value = null; refresh();
  } catch (e) { err.value = e.message; } finally { busy.value = false; }
}
async function setSetEnabled(s, on) { await api.skillSets.update(s.id, { enabled: on }); refresh(); }
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Automation" title="AI skills"
                  subtitle="The AI picks one skill per incident. Every tool only reads data. Write your own skills, give any skill your team's instructions, and group skills for parts of your estate.">
      <UiButton icon="add" @click="open()">New skill</UiButton>
    </UiPageHeader>
    <UiSkeletonPage v-if="!skills" />
    <template v-else>
      <!-- your skills -->
      <section class="block">
        <div class="block__head"><div><h3>Your skills</h3><p class="sub">Each one runs the built-in investigation for its incident kinds first, then its own tools, and hands the AI your instructions.</p></div></div>
        <div v-if="yours.length" class="grid">
          <article v-for="s in yours" :key="s.id" :class="['sk', { off: !s.enabled }]">
            <div class="sk__top"><UiGlyph name="sparkle" :size="34" /><div class="sk__t"><h4>{{ s.name }}</h4><p class="sub">{{ s.description || "Written by your team" }}</p></div>
              <UiSwitch :model-value="s.enabled" :label="`Use ${s.name}`" @update:model-value="(v) => setEnabled(s, v)" /></div>
            <div class="chips"><span v-for="k in s.kinds" :key="k" class="chip">{{ kindLabel(k) }}</span></div>
            <p v-if="s.instructions" class="note">{{ s.instructions }}</p>
            <div class="sk__foot"><span class="muted small">{{ (s.tools || []).length }} extra tool{{ (s.tools || []).length === 1 ? "" : "s" }} · used {{ s.runs }}× · rating {{ s.avg_score ?? "–" }}</span>
              <div class="row"><UiButton size="sm" variant="tint" @click="open(s)">Edit</UiButton>
                <UiButton size="sm" :variant="armed === `skill:${s.id}` ? 'danger' : 'ghost'" @click="remove('skill', s)">{{ armed === `skill:${s.id}` ? "Click to confirm" : "Delete" }}</UiButton></div></div>
          </article>
        </div>
        <button v-else type="button" class="empty" @click="open()">
          <UiSpot glyph="sparkle" hue="sky" badge="plus" :size="64" />
          <span><b>Write your first skill</b><span class="muted">Say what to check for an incident kind, in your team's words. For example: "For payments, check the card gateway log before anything else."</span></span>
        </button>
      </section>

      <!-- skill sets -->
      <section class="block">
        <div class="block__head"><div><h3>Skill sets</h3><p class="sub">Which skills investigate which services or hosts. An incident on <span class="mono">pay-*</span> uses only that set's skills, unless none of them fits its kind.</p></div>
          <UiButton size="sm" variant="tint" icon="add" @click="openSet()">New skill set</UiButton></div>
        <div v-if="sets.length" class="sets">
          <div v-for="s in sets" :key="s.id" :class="['set', { off: !s.enabled }]">
            <div class="set__main"><b>{{ s.name }}</b><span class="mono small muted">{{ s.scope || "no scope" }}</span></div>
            <div class="chips"><span v-for="id in s.skills" :key="id" class="chip chip--sky">{{ nameOf(id) }}</span></div>
            <div class="row"><UiSwitch :model-value="s.enabled" :label="`Use ${s.name}`" @update:model-value="(v) => setSetEnabled(s, v)" />
              <UiButton size="sm" variant="ghost" @click="openSet(s)">Edit</UiButton>
              <UiButton size="sm" :variant="armed === `set:${s.id}` ? 'danger' : 'ghost'" @click="remove('set', s)">{{ armed === `set:${s.id}` ? "Click to confirm" : "Delete" }}</UiButton></div>
          </div>
        </div>
        <p v-else class="muted small">No skill sets. Every skill can investigate every service.</p>
      </section>

      <!-- built-in -->
      <section class="block">
        <div class="block__head"><div><h3>Built-in skills</h3><p class="sub">Switch one off, or add instructions the AI reads every time it uses it.</p></div></div>
        <div class="grid">
          <article v-for="s in builtin" :key="s.id" :class="['sk', { off: !s.enabled }]">
            <div class="sk__top"><UiGlyph :name="s.category === 'Security' ? 'inc_auth' : s.category === 'Infrastructure' ? 'server' : 'service'" :size="34" />
              <div class="sk__t"><h4>{{ s.name }}</h4><p class="sub">{{ s.description }}</p></div>
              <UiSwitch :model-value="s.enabled" :label="`Use ${s.name}`" @update:model-value="(v) => setEnabled(s, v)" /></div>
            <div class="chips"><span v-for="k in s.kinds" :key="k" class="chip">{{ kindLabel(k) }}</span></div>
            <p v-if="s.instructions" class="note">{{ s.instructions }}</p>
            <div class="stats"><div><span>Used</span><b>{{ s.runs }}</b></div><div><span>Rating</span><b>{{ s.avg_score ?? "–" }}</b></div>
              <div><span>Correct</span><b>{{ s.accuracy == null ? "–" : `${Math.round(s.accuracy * 100)}%` }}</b></div><div><span>Takes</span><b>{{ s.avg_analysis_s ?? "–" }} s</b></div></div>
            <div v-if="s.lessons?.length" class="small lessons"><b>Learning from feedback</b><div v-for="l in s.lessons" :key="l" class="muted">· {{ l }}</div></div>
            <div class="sk__foot"><span class="muted small mono">{{ (s.tools || []).length }} tools</span><UiButton size="sm" variant="tint" @click="open(s)">Instructions</UiButton></div>
          </article>
        </div>
      </section>
    </template>

    <!-- skill editor -->
    <UiSheet :model-value="!!editing" :title="isBuiltin ? editing?.name : editing?.id ? `Edit ${editing.name}` : 'New skill'" :width="640"
             @update:model-value="editing = null">
      <template v-if="editing">
        <p v-if="isBuiltin" class="sub">The tools of a built-in skill are part of RadarOps. What you can change: whether it runs, and what the AI should keep in mind.</p>
        <template v-else>
          <UiField v-model="form.name" label="Name" placeholder="e.g. Payments errors" />
          <UiField v-model="form.description" label="What it is for" hint="optional" placeholder="Card payments failing or slow" />
          <p class="lbl">Runs on these incident kinds</p>
          <div class="chips"><button v-for="k in catalog.kinds" :key="k" type="button" :class="['chip', 'chip--btn', { on: form.kinds.includes(k) }]"
                                     :aria-pressed="form.kinds.includes(k)" @click="form.kinds = toggle(form.kinds, k)">{{ kindLabel(k) }}</button></div>
          <p class="lbl">Extra tools <span class="muted">· all read-only</span></p>
          <div class="tools">
            <label v-for="(t, id) in catalog.tools" :key="id" :class="['tool', { on: form.tools.includes(id) }]">
              <input type="checkbox" :checked="form.tools.includes(id)" @change="form.tools = toggle(form.tools, id)">
              <span>{{ t.label }}<small>{{ t.on === "any" ? "any incident" : `${t.on} incidents` }}</small></span>
            </label>
          </div>
        </template>
        <UiField v-model="form.instructions" multiline label="Instructions for the AI" hint="optional · read with the evidence every time"
                 placeholder="Check the card gateway log first. A spike right after 02:00 is the nightly batch, not an outage." />
        <label class="switch-row"><span>Use this skill</span><UiSwitch v-model="form.enabled" label="Use this skill" /></label>
        <p v-if="err" class="err">{{ err }}</p>
      </template>
      <template #footer>
        <UiButton variant="ghost" @click="editing = null">Cancel</UiButton>
        <UiButton :loading="busy" :disabled="!isBuiltin && (!form.name.trim() || !form.kinds.length)" @click="save">Save</UiButton>
      </template>
    </UiSheet>

    <!-- skill set editor -->
    <UiSheet :model-value="!!setEditing" :title="setEditing?.id ? `Edit ${setEditing.name}` : 'New skill set'" @update:model-value="setEditing = null">
      <template v-if="setEditing">
        <UiField v-model="setForm.name" label="Name" placeholder="e.g. Payments" />
        <UiField v-model="setForm.scope" mono label="Services or hosts" hint="comma separated · * matches anything" placeholder="pay-*, checkout" />
        <p class="lbl">Skills in this set</p>
        <div class="chips"><button v-for="s in skills" :key="s.id" type="button" :class="['chip', 'chip--btn', { on: setForm.skills.includes(s.id) }]"
                                   :aria-pressed="setForm.skills.includes(s.id)" @click="setForm.skills = toggle(setForm.skills, s.id)">{{ s.name }}</button></div>
        <p v-if="err" class="err">{{ err }}</p>
      </template>
      <template #footer>
        <UiButton variant="ghost" @click="setEditing = null">Cancel</UiButton>
        <UiButton :loading="busy" :disabled="!setForm.name.trim() || !setForm.skills.length" @click="saveSet">Save</UiButton>
      </template>
    </UiSheet>
  </div>
</template>
<style scoped>
.block { margin-bottom: 28px; }
.block__head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 14px; }
.block h3 { font-size: 18px; font-weight: var(--fw-semibold); letter-spacing: -0.01em; }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 4px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }
.sk { background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; }
.sk.off, .set.off { opacity: 0.55; }
.sk__top { display: flex; gap: 12px; align-items: flex-start; }
.sk__t { flex: 1; min-width: 0; }
.sk h4 { font-size: 16px; font-weight: var(--fw-semibold); }
.sk__foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: auto; flex-wrap: wrap; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; padding: 3px 10px; border-radius: 999px; background: var(--c-fill); color: var(--c-text-2); border: 1px solid transparent; }
.chip--sky { background: color-mix(in srgb, #acdcf3 22%, transparent); color: var(--c-text); }
.chip--btn { cursor: pointer; font-size: 13px; padding: 5px 12px; border-color: var(--c-border); }
.chip--btn.on { background: var(--c-primary-tint); border-color: color-mix(in srgb, var(--c-primary) 55%, transparent); color: var(--c-text); }
.note { font-size: var(--fs-sm); color: var(--c-text-2); background: var(--c-fill); border-left: 3px solid #cbbcf4; padding: 8px 12px; border-radius: 6px; white-space: pre-line; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.stats span { display: block; font-size: 12px; color: var(--c-text-3); }
.lessons { border-top: 1px solid var(--c-border); padding-top: 10px; }
.empty { width: 100%; display: flex; align-items: center; gap: 18px; text-align: left; padding: 18px 22px; border-radius: var(--radius-lg);
  background: var(--surface); box-shadow: var(--shadow-card); border: 1px dashed var(--c-border); color: var(--c-text); cursor: pointer; }
.empty b { display: block; margin-bottom: 4px; }
.empty .muted { font-size: var(--fs-sm); }
.sets { display: flex; flex-direction: column; gap: 8px; }
.set { display: grid; grid-template-columns: 220px 1fr auto; gap: 16px; align-items: center; background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 12px 16px; }
.set__main { display: flex; flex-direction: column; gap: 2px; }
.lbl { font-size: var(--fs-sm); color: var(--c-text-2); margin: 16px 0 8px; font-weight: var(--fw-medium); }
.tools { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }
.tool { display: flex; gap: 10px; align-items: flex-start; padding: 8px 10px; border-radius: var(--radius-md); border: 1px solid var(--c-border); cursor: pointer; font-size: var(--fs-sm); }
.tool.on { border-color: color-mix(in srgb, var(--c-primary) 55%, transparent); background: var(--c-primary-tint); }
.tool input { margin-top: 3px; accent-color: var(--c-primary); }
.tool small { display: block; color: var(--c-text-3); font-size: 12px; }
.switch-row { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; font-size: var(--fs-sm); color: var(--c-text-2); }
.err { color: var(--c-bad-text); margin-top: 10px; }
@media (max-width: 760px) { .set { grid-template-columns: 1fr; } .tools { grid-template-columns: 1fr; } .grid { grid-template-columns: 1fr; } }
</style>
