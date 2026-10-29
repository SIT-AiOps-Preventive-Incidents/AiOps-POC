<script setup>
/**
 * Runbooks - fixes the team already knows. Two sources: the AI learns one when a fix works and is rated 4-5 stars,
 * and a team writes one for a problem it already knows how to solve. Both are found the same way (incident kind +
 * service + fix), so a known problem is solved from its runbook instead of a fresh investigation.
 */
import { computed, ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { FIX_LABEL, kindLabel, runbookBody, runbookForm } from "@/lib/automation";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const rbs = ref(null);
const catalog = ref({ kinds: [], fix_types: [] });
const { refresh } = usePolling(async () => { rbs.value = await api.runbooks.list(); }, 30000);
api.automation.catalog().then((c) => (catalog.value = c));
async function toggle(r) { await api.runbooks.setEnabled(r.id, !r.enabled); refresh(); }
const filter = ref("all");
const FILTERS = [{ value: "all", label: "All" }, { value: "written", label: "Written by the team" }, { value: "learned", label: "Learned by the AI" }];
const shown = computed(() => (rbs.value || []).filter((r) => filter.value === "all" || (filter.value === "written") === !!r.authored));

const editing = ref(null);
const form = ref(runbookForm());
const err = ref("");
const busy = ref(false);
const open = (r = {}) => { editing.value = r; form.value = runbookForm(r); err.value = ""; };
const ready = computed(() => form.value.title.trim() && form.value.service.trim() && form.value.stepsText.trim());
async function save() {
  busy.value = true; err.value = "";
  try {
    await (editing.value.id ? api.runbooks.update(editing.value.id, runbookBody(form.value)) : api.runbooks.create(runbookBody(form.value)));
    ui.toast(`Saved ${form.value.title}`); editing.value = null; refresh();
  } catch (e) { err.value = e.message; } finally { busy.value = false; }
}
const armed = ref(null);
async function remove(r) {
  if (armed.value !== r.id) { armed.value = r.id; setTimeout(() => { if (armed.value === r.id) armed.value = null; }, 4000); return; }
  armed.value = null; await api.runbooks.remove(r.id); ui.toast(`Deleted RB-${r.id}`); editing.value = null; refresh();
}
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Automation" title="Runbooks"
                  subtitle="Fixes your team knows. The AI learns one each time a fix works and is rated 4-5 stars, and you can write your own. When the same problem comes back, the AI uses the runbook instead of starting over.">
      <UiButton icon="add" @click="open()">Write a runbook</UiButton>
    </UiPageHeader>
    <UiSkeletonPage v-if="!rbs" />
    <template v-else>
      <div class="bar"><UiSegmented v-model="filter" :options="FILTERS" label="Show" /></div>
      <UiList>
        <UiListRow v-for="r in shown" :key="r.id" :title="`RB-${r.id} ${r.title}`" :detail="r.root_cause"
                   :subtitle="`${kindLabel(r.kind)} · ${r.action_params?.service || 'any'} · ${FIX_LABEL[r.action_type] || r.action_type} · used ${r.uses}× · ${(r.steps || []).length} steps`">
          <template #leading><UiAppTile icon="book" :color="r.enabled ? 'var(--c-chart-5)' : 'var(--c-neutral)'" /></template>
          <template #accessory>
            <span :class="['src', r.authored ? 'src--team' : 'src--ai']">{{ r.authored ? "Team" : "AI" }}</span>
            <router-link v-if="r.source_incident_id" :to="`/problems/${r.source_incident_id}`" class="small">P-{{ r.source_incident_id }}</router-link>
            <UiButton v-if="r.authored" size="sm" variant="ghost" @click="open(r)">Edit</UiButton>
            <UiSwitch :model-value="r.enabled" :label="`Use RB-${r.id}`" @update:model-value="toggle(r)" />
          </template>
        </UiListRow>
        <UiEmpty v-if="!shown.length">{{ filter === "written" ? "No runbooks written yet. Write one for a problem your team already knows how to fix." : "No runbooks yet. Resolve a problem and rate it 4-5 stars, or write one." }}</UiEmpty>
      </UiList>
    </template>

    <UiSheet :model-value="!!editing" :title="editing?.id ? `Edit RB-${editing.id}` : 'Write a runbook'" :width="620" @update:model-value="editing = null">
      <template v-if="editing">
        <p class="sub">The AI finds a runbook by incident kind, service and fix. Write what your best engineer would do.</p>
        <UiField v-model="form.title" label="Title" placeholder="e.g. Checkout errors after a release" />
        <div class="two">
          <label class="sel"><span>Incident kind</span>
            <select v-model="form.kind"><option v-for="k in catalog.kinds" :key="k" :value="k">{{ kindLabel(k) }}</option></select></label>
          <UiField v-model="form.service" mono label="Service or host" placeholder="checkout" />
        </div>
        <label class="sel"><span>The fix</span>
          <select v-model="form.action_type"><option v-for="f in catalog.fix_types" :key="f" :value="f">{{ FIX_LABEL[f] || f }}</option></select></label>
        <UiField v-model="form.root_cause" label="Usual cause" hint="optional" placeholder="A release that breaks the card gateway client" />
        <UiField v-model="form.stepsText" multiline label="Steps" hint="one per line" placeholder="Check the last deploy of checkout&#10;Roll back to the previous version&#10;Watch the failure rate for 5 minutes" />
        <p class="sub">The fix still goes through its dry run and waits for a person to approve it.</p>
        <p v-if="err" class="err">{{ err }}</p>
      </template>
      <template #footer>
        <UiButton v-if="editing?.id" :variant="armed === editing.id ? 'danger' : 'ghost'" @click="remove(editing)">{{ armed === editing.id ? "Click to confirm" : "Delete" }}</UiButton>
        <span class="grow" />
        <UiButton variant="ghost" @click="editing = null">Cancel</UiButton>
        <UiButton :loading="busy" :disabled="!ready" @click="save">Save</UiButton>
      </template>
    </UiSheet>
  </div>
</template>
<style scoped>
.bar { margin-bottom: 14px; }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 6px; }
.src { font-size: 12px; padding: 2px 9px; border-radius: 999px; font-weight: var(--fw-semibold); }
.src--team { background: color-mix(in srgb, #f9cba9 30%, transparent); color: var(--c-text); }
.src--ai { background: color-mix(in srgb, #cbbcf4 30%, transparent); color: var(--c-text); }
.two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: end; }
.sel { display: block; }
.sel span { display: block; font-size: var(--fs-sm); color: var(--c-text-2); margin: 14px 0 7px; font-weight: var(--fw-medium); }
.sel select { width: 100%; background: var(--c-fill); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 10px 12px; font-size: var(--fs-md); color: var(--c-text); }
.sel select:focus { outline: none; border-color: var(--c-primary); box-shadow: 0 0 0 3px var(--c-primary-tint); }
.grow { flex: 1; }
.err { color: var(--c-bad-text); margin-top: 10px; }
@media (max-width: 760px) { .two { grid-template-columns: 1fr; } }
</style>
