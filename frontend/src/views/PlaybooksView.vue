<script setup>
/**
 * Playbooks - what happens when an incident happens: which team gets it, and when to escalate if nobody approves the
 * fix in time. A playbook never applies a fix on its own; every fix still waits for a person.
 */
import { computed, ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { kindLabel, playbookBody, playbookForm, playbookSentence, toggle } from "@/lib/automation";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const pbs = ref(null);
const teams = ref([]);
const catalog = ref({ kinds: [], severities: [] });
const { refresh } = usePolling(async () => { pbs.value = await api.playbooks.list(); }, 30000);
api.automation.catalog().then((c) => (catalog.value = c));
api.teams().then((t) => (teams.value = t));
const SEVERITIES = [{ value: "", label: "Any" }, { value: "minor", label: "Minor+" }, { value: "major", label: "Major+" }, { value: "critical", label: "Critical" }];

const editing = ref(null);
const form = ref(playbookForm());
const err = ref("");
const busy = ref(false);
const open = (p = {}) => { editing.value = p; form.value = playbookForm(p); err.value = ""; };
const preview = computed(() => playbookSentence(playbookBody(form.value)));
async function save() {
  busy.value = true; err.value = "";
  try {
    const body = playbookBody(form.value);
    await (editing.value.id ? api.playbooks.update(editing.value.id, body) : api.playbooks.create(body));
    ui.toast(`Saved ${body.name}`); editing.value = null; refresh();
  } catch (e) { err.value = e.message; } finally { busy.value = false; }
}
async function setEnabled(p, on) { await api.playbooks.update(p.id, { enabled: on }); refresh(); }
const armed = ref(null);
async function remove(p) {
  if (armed.value !== p.id) { armed.value = p.id; setTimeout(() => { if (armed.value === p.id) armed.value = null; }, 4000); return; }
  armed.value = null; await api.playbooks.remove(p.id); ui.toast(`Deleted ${p.name}`); editing.value = null; refresh();
}
// a ready-made starting point, so the first playbook is one click from useful
const STARTERS = [
  { name: "Critical: escalate after 15 minutes", trigger: { min_severity: "critical" }, actions: { escalate_after_min: 15 } },
  { name: "Login attacks go to security", trigger: { kinds: ["auth_bruteforce"] }, actions: { owner_team: "team-security", escalate_after_min: 10 } },
  { name: "Disk and memory go to platform", trigger: { kinds: ["host_disk", "host_mem"] }, actions: { owner_team: "team-platform", escalate_after_min: 60 } },
];
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Automation" title="Playbooks"
                  subtitle="Your team's rules for incidents: who gets which incident, and who hears about it when a fix waits too long for approval. A playbook never applies a fix; every fix waits for a person.">
      <UiButton icon="add" @click="open()">New playbook</UiButton>
    </UiPageHeader>
    <UiSkeletonPage v-if="!pbs" />
    <template v-else>
      <div v-if="pbs.length" class="list">
        <article v-for="p in pbs" :key="p.id" :class="['pb', { off: !p.enabled }]">
          <UiGlyph name="playbook" :size="34" />
          <div class="pb__main">
            <h4>{{ p.name }}</h4>
            <p class="rule">{{ playbookSentence(p) }}</p>
          </div>
          <div class="pb__runs"><b>{{ p.runs }}</b><span>times applied</span></div>
          <div class="row">
            <UiSwitch :model-value="p.enabled" :label="`Use ${p.name}`" @update:model-value="(v) => setEnabled(p, v)" />
            <UiButton size="sm" variant="tint" @click="open(p)">Edit</UiButton>
          </div>
        </article>
      </div>
      <section v-else class="start">
        <h3>Start from one of these</h3>
        <p class="sub">Each opens in the editor, so you can change it before saving.</p>
        <div class="starters">
          <button v-for="s in STARTERS" :key="s.name" type="button" class="starter" @click="open(); form = playbookForm(s)">
            <UiSpot glyph="playbook" hue="peach" badge="plus" :size="56" />
            <span><b>{{ s.name }}</b><span class="muted small">{{ playbookSentence(s) }}</span></span>
          </button>
        </div>
      </section>
    </template>

    <UiSheet :model-value="!!editing" :title="editing?.id ? `Edit ${editing.name}` : 'New playbook'" :width="620" @update:model-value="editing = null">
      <template v-if="editing">
        <UiField v-model="form.name" label="Name" placeholder="e.g. Payments on-call" />
        <p class="lbl">When the incident is <span class="muted">· none picked = any kind</span></p>
        <div class="chips"><button v-for="k in catalog.kinds" :key="k" type="button" :class="['chip', { on: form.kinds.includes(k) }]"
                                   :aria-pressed="form.kinds.includes(k)" @click="form.kinds = toggle(form.kinds, k)">{{ kindLabel(k) }}</button></div>
        <p class="lbl">Severity</p>
        <UiSegmented v-model="form.min_severity" :options="SEVERITIES" label="Severity" />
        <UiField v-model="form.entity" mono label="On services or hosts" hint="optional · comma separated · * matches anything" placeholder="checkout*, pay-*" />
        <div class="two">
          <label class="sel"><span>Hand it to</span>
            <select v-model="form.owner_team"><option value="">The service's own team</option>
              <option v-for="t in teams" :key="t.id" :value="t.name">{{ t.name }}</option></select></label>
          <UiField v-model="form.escalate" type="number" label="Escalate after (minutes)" hint="optional" placeholder="30" />
        </div>
        <p class="preview">{{ preview }}</p>
        <label class="switch-row"><span>Use this playbook</span><UiSwitch v-model="form.enabled" label="Use this playbook" /></label>
        <p v-if="err" class="err">{{ err }}</p>
      </template>
      <template #footer>
        <UiButton v-if="editing?.id" :variant="armed === editing.id ? 'danger' : 'ghost'" @click="remove(editing)">{{ armed === editing.id ? "Click to confirm" : "Delete" }}</UiButton>
        <span class="grow" />
        <UiButton variant="ghost" @click="editing = null">Cancel</UiButton>
        <UiButton :loading="busy" :disabled="!form.name.trim()" @click="save">Save</UiButton>
      </template>
    </UiSheet>
  </div>
</template>
<style scoped>
.list { display: flex; flex-direction: column; gap: 10px; }
.pb { display: grid; grid-template-columns: auto 1fr auto auto; gap: 16px; align-items: center; background: var(--surface);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 16px 20px; }
.pb.off { opacity: 0.55; }
.pb h4 { font-size: 16px; font-weight: var(--fw-semibold); }
.rule { font-size: var(--fs-sm); color: var(--c-text-2); margin-top: 4px; }
.pb__runs { text-align: right; }
.pb__runs b { display: block; font-size: 20px; }
.pb__runs span { font-size: 12px; color: var(--c-text-3); }
.start h3 { font-size: 18px; font-weight: var(--fw-semibold); }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 4px; }
.starters { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; margin-top: 14px; }
.starter { display: flex; gap: 14px; align-items: center; text-align: left; padding: 14px 16px; border-radius: var(--radius-lg);
  background: var(--surface); box-shadow: var(--shadow-card); border: 1px dashed var(--c-border); color: var(--c-text); cursor: pointer; }
.starter b { display: block; margin-bottom: 4px; }
.lbl { font-size: var(--fs-sm); color: var(--c-text-2); margin: 16px 0 8px; font-weight: var(--fw-medium); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 13px; padding: 5px 12px; border-radius: 999px; background: var(--c-fill); color: var(--c-text-2); border: 1px solid var(--c-border); cursor: pointer; }
.chip.on { background: var(--c-primary-tint); border-color: color-mix(in srgb, var(--c-primary) 55%, transparent); color: var(--c-text); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: end; }
.sel { display: block; }
.sel span { display: block; font-size: var(--fs-sm); color: var(--c-text-2); margin: 14px 0 7px; font-weight: var(--fw-medium); }
.sel select { width: 100%; background: var(--c-fill); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 10px 12px; font-size: var(--fs-md); color: var(--c-text); }
.preview { margin-top: 16px; padding: 10px 14px; border-radius: var(--radius-md); background: color-mix(in srgb, #f9cba9 16%, transparent); font-size: var(--fs-sm); }
.switch-row { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; font-size: var(--fs-sm); color: var(--c-text-2); }
.grow { flex: 1; }
.err { color: var(--c-bad-text); margin-top: 10px; }
@media (max-width: 760px) { .pb { grid-template-columns: auto 1fr; } .two { grid-template-columns: 1fr; } }
</style>
