<script setup>
// The owner's decision card: recommended fix + dry-run checklist + owner confirmation + approve / reject.
import { computed, ref, watch } from "vue";
import { useIncidentStore } from "@/stores/incidents";
import { useUiStore } from "@/stores/ui";
import DryRunChecklist from "./DryRunChecklist.vue";

const props = defineProps({ incident: { type: Object, required: true } });
const store = useIncidentStore();
const ui = useUiStore();
const inc = computed(() => props.incident);
const waiting = computed(() => ["awaiting_approval", "remediation_failed"].includes(inc.value.status));
const investigating = computed(() => ["open", "analyzing"].includes(inc.value.status));
const cands = computed(() => inc.value.candidates || []);
const pick = ref(0);
const chosen = computed(() => cands.value[pick.value] || inc.value.action);
const ownerOk = ref(false);
const approver = ref(ui.prefs.approver || "");
const comment = ref("");
const busy = ref("");
watch(() => inc.value.id, () => { pick.value = 0; ownerOk.value = false; });
const canApprove = computed(() => chosen.value?.dry_run?.ok && ownerOk.value && approver.value.trim());
const ap = computed(() => inc.value.approval);

async function decide(decision) {
  busy.value = decision;
  ui.setPref("approver", approver.value.trim());
  try {
    await store.decide(inc.value.id, { decision, candidate_id: chosen.value?.id, approver: approver.value.trim() || "owner",
      owner_confirmed: ownerOk.value, comment: comment.value });
    ui.toast(decision === "approve" ? "Approved. Applying the fix." : "Rejected");
  } catch (e) {
    const failed = e.details?.failed_checks?.map((c) => c.name).join(", ");
    ui.toast(failed ? `${e.message}: ${failed}` : e.message);
    await store.load(inc.value.id);
  } finally {
    busy.value = "";
  }
}
</script>
<template>
  <UiCard :title="waiting || investigating ? 'Recommended fix' : 'Fix'">
    <UiWait v-if="investigating" title="The AI is investigating" :subtitle="`${inc.steps.length} steps so far · usually 1-3 minutes`" />

    <template v-else-if="waiting && chosen">
      <div class="fix"><div class="small muted">{{ pick === 0 ? "AI recommends" : "You picked" }}</div><div class="fix__a">{{ chosen.label }}</div></div>
      <DryRunChecklist class="mt" :dry-run="chosen.dry_run" />
      <div class="owner">
        <div><div class="b">I'm the owner</div><div class="small muted">{{ inc.owner || "unassigned" }} approves this fix</div></div>
        <UiSwitch v-model="ownerOk" label="I am the owner" />
      </div>
      <UiField v-model="approver" label="Your name" placeholder="e.g. Napat" autocomplete="name" />
      <UiButton class="mt" size="lg" block :disabled="!canApprove" :loading="busy === 'approve'" @click="decide('approve')">
        {{ chosen.type === "manual" ? "Acknowledge - I'll handle it" : "Approve fix" }}</UiButton>
      <div class="row row--between mt-2">
        <UiButton variant="danger" :loading="busy === 'reject'" @click="decide('reject')">Reject</UiButton>
        <span class="small dim">Checked again right before it runs</span>
      </div>
      <UiDisclosure v-if="cands.length > 1" :card="false" :title="`Other options (${cands.length - 1})`" class="mt-2">
        <label v-for="(c, i) in cands" :key="c.id" :class="['alt', { sel: i === pick, blocked: !c.dry_run?.ok }]">
          <input type="radio" name="cand" :checked="i === pick" :disabled="!c.dry_run?.ok" @change="pick = i">
          <span><b>{{ c.label }}</b><span v-if="i === 0" class="small muted"> · recommended</span>
            <span :class="['small', 'block', c.dry_run?.ok ? 'ok' : 'bad']">{{ c.dry_run?.ok ? "Dry run passed" : "Dry run failed: " + (c.dry_run?.checks || []).filter((x) => !x.ok).map((x) => x.name).join(", ") }}</span></span>
        </label>
      </UiDisclosure>
      <UiField v-model="comment" label="Comment (optional)" placeholder="Why approve or reject" />
    </template>

    <template v-else>
      <div class="fix"><div class="fix__a">{{ inc.action?.label || "No action" }}</div></div>
      <dl v-if="ap" class="kv mt">
        <dt>{{ ap.decision === "rejected" ? "Rejected by" : "Approved by" }}</dt><dd>{{ ap.approver }}<span v-if="ap.owner"> for {{ ap.owner }}</span></dd>
        <template v-if="ap.preflight"><dt>Re-checked</dt><dd :class="ap.preflight.ok ? 'ok' : 'bad'">{{ ap.preflight.ok ? "Dry run passed again before applying" : "Pre-flight failed" }}</dd></template>
        <template v-if="ap.execution"><dt>Result</dt><dd :class="ap.execution.ok ? 'ok' : 'bad'">{{ ap.execution.detail }}</dd></template>
        <template v-if="ap.execution && ap.execution.verified != null"><dt>Verified</dt><dd :class="ap.execution.verified ? 'ok' : 'bad'">{{ ap.execution.verified ? "Metrics back to normal" : "Still abnormal" }}</dd></template>
        <template v-if="inc.status === 'verifying'"><dt>Status</dt><dd class="muted">Checking the metrics...</dd></template>
      </dl>
    </template>
  </UiCard>
</template>
<style scoped>
.fix { border-radius: 12px; background: var(--c-primary-tint); padding: 14px 16px; }
.fix__a { font-size: var(--fs-lg); font-weight: var(--fw-semibold); }
.owner { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 0; border-top: 0.5px solid var(--c-separator); border-bottom: 0.5px solid var(--c-separator); margin: 14px 0 4px; }
.b { font-weight: var(--fw-semibold); }
.alt { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: 10px; cursor: pointer; margin-top: 6px; background: var(--c-fill); }
.alt.sel { background: var(--c-primary-tint); box-shadow: inset 0 0 0 1.5px var(--c-primary); }
.alt.blocked { opacity: 0.6; cursor: not-allowed; }
.alt input { margin-top: 4px; }
.block { display: block; }
.kv { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 6px 10px; font-size: 14px; margin-bottom: 0; }
.kv dt { color: var(--c-text-2); } .kv dd { margin: 0; }
</style>
