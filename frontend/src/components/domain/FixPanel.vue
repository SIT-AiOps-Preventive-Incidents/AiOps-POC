<script setup>
// The owner's decision card: recommended fix + dry-run checklist + owner confirmation + approve / reject.
import { computed, ref, watch } from "vue";
import { clock } from "@/lib/format";
import { useIncidentStore } from "@/stores/incidents";
import { useUiStore } from "@/stores/ui";
import { approveLabel, consequence } from "@/lib/insight";
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
const will = computed(() => consequence(chosen.value));

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
  <UiCard :title="waiting || investigating ? 'Recommended fix' : 'Fix'" :icon="waiting || investigating ? 'wrench' : undefined">
    <UiWait v-if="investigating" title="The AI is investigating" :subtitle="`${inc.steps.length} steps so far, usually 1 to 3 minutes`" />

    <template v-else-if="waiting && chosen">
      <div class="fix">
        <span class="fix__tag"><UiIcon name="sparkle" :size="13" />{{ pick === 0 ? "AI recommends" : "You picked" }}</span>
        <div class="fix__a">{{ chosen.label }}</div>
      </div>
      <section v-if="will" class="will" aria-label="If you approve">
        <div class="will__t"><UiIcon name="play" :size="13" />If you approve</div>
        <p v-if="will.manual" class="small">Nothing runs automatically. You confirm that you will follow the runbook yourself.</p>
        <template v-else>
          <p class="small">AIOps One will run:</p>
          <pre class="will__cmd">{{ will.runs.join("\n") || chosen.label }}</pre>
          <p v-if="will.impact" class="small"><span class="muted">Who notices:</span> {{ will.impact }}</p>
        </template>
      </section>
      <DryRunChecklist class="mt" :dry-run="chosen.dry_run" :effects="false" />

      <!-- the decision: one clear "your turn" block (orange). Fill the two fields, then the one bold action. -->
      <div class="decision">
        <div class="decision__h"><UiIcon name="person" :size="15" />Your decision</div>
        <div class="decision__form">
          <UiField v-model="approver" label="Your name" placeholder="e.g. Napat" autocomplete="name" />
          <label class="owner">
            <UiSwitch v-model="ownerOk" label="I am the owner" />
            <span><span class="b">I'm the owner of {{ inc.owner || "this service" }}</span><span class="small muted">and take responsibility for this fix</span></span>
          </label>
        </div>
        <UiButton variant="action" size="lg" block icon="checkmark" :class="{ 'is-waiting': !canApprove }"
                  :disabled="!canApprove" :loading="busy === 'approve'" @click="decide('approve')">
          {{ approveLabel(chosen) }}</UiButton>
        <p :class="['caption', canApprove ? 'ok' : 'dim']">
          <UiIcon :name="canApprove ? 'shield' : 'alert'" :size="13" />
          {{ canApprove ? "AIOps re-checks the dry run right before it runs." : !chosen.dry_run?.ok ? "The dry run failed, so this fix cannot be approved." : !ownerOk ? "Turn on “I’m the owner” to enable approval." : "Enter your name to enable approval." }}
        </p>
        <UiButton variant="ghost" block icon="dismiss" class="reject" :loading="busy === 'reject'" @click="decide('reject')">Reject this fix</UiButton>
        <UiField v-model="comment" class="cmt" label="Comment (optional)" placeholder="Why approve or reject" />
      </div>

      <UiDisclosure v-if="cands.length > 1" :card="false" :title="`Other options (${cands.length - 1})`" class="mt-2">
        <label v-for="(c, i) in cands" :key="c.id" :class="['alt', { sel: i === pick, blocked: !c.dry_run?.ok }]">
          <input type="radio" name="cand" :checked="i === pick" :disabled="!c.dry_run?.ok" @change="pick = i">
          <span><b>{{ c.label }}</b><span v-if="i === 0" class="small muted"> (recommended)</span>
            <span :class="['small', 'block', c.dry_run?.ok ? 'ok' : 'bad']">{{ c.dry_run?.ok ? "Dry run passed" : "Dry run failed: " + (c.dry_run?.checks || []).filter((x) => !x.ok).map((x) => x.name).join(", ") }}</span></span>
        </label>
      </UiDisclosure>
    </template>

    <template v-else>
      <div class="fix"><div class="fix__a">{{ inc.action?.label || "No action" }}</div></div>
      <dl v-if="ap" class="kv mt">
        <dt>{{ ap.decision === "rejected" ? "Rejected by" : "Approved by" }}</dt><dd>{{ ap.approver }}<span v-if="ap.owner"> for {{ ap.owner }}</span><span class="muted"> · {{ clock(ap.decided_at) }}</span></dd>
        <template v-if="ap.preflight"><dt>Re-checked</dt><dd :class="ap.preflight.ok ? 'ok' : 'bad'">{{ ap.preflight.ok ? "Dry run passed again before applying" : "Pre-flight failed" }}</dd></template>
        <template v-if="ap.execution"><dt>Result</dt><dd :class="ap.execution.ok ? 'ok' : 'bad'">{{ ap.execution.detail }}</dd></template>
        <template v-if="ap.execution && ap.execution.verified != null"><dt>Verified</dt><dd :class="ap.execution.verified ? 'ok' : 'bad'">{{ ap.execution.verified ? "Metrics back to normal" : "Still abnormal" }}</dd></template>
        <template v-if="inc.status === 'verifying'"><dt>Status</dt><dd class="muted">Checking the metrics…</dd></template>
      </dl>
    </template>
  </UiCard>
</template>
<style scoped>
.fix { border-radius: var(--radius-md); background: var(--c-primary-tint); padding: 12px 14px; }
.fix__tag { display: inline-flex; align-items: center; gap: 5px; font-size: var(--fs-xs); font-weight: var(--fw-semibold); color: var(--c-primary); margin-bottom: 2px; }
.fix__a { font-size: var(--fs-lg); font-weight: var(--fw-semibold); }
.b { font-weight: var(--fw-semibold); display: block; }
.will { margin-top: 12px; padding: 10px 12px; border-radius: var(--radius-md); border: 1px solid var(--c-border); }
.will__t { display: flex; align-items: center; gap: 6px; font-size: var(--fs-xs); font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.04em; color: var(--c-action-text, var(--c-action)); margin-bottom: 4px; }
.will p { margin: 4px 0; }
.will__cmd { background: var(--c-fill); border-radius: 8px; padding: 8px 10px; font: 12px/1.5 var(--font-mono); white-space: pre-wrap; margin: 4px 0; }

/* the decision: the one place that needs a person. Grouped and tinted so the action reads as "your turn". */
.decision { margin-top: 16px; padding: 14px; border: 1px solid var(--c-action); border-radius: var(--radius-lg); background: var(--c-action-bg); }
.decision__h { display: flex; align-items: center; gap: 7px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-action-text); margin-bottom: 10px; }
.decision__h .ui-icon { color: var(--c-action); }
/* name + owner grouped in one clean white panel */
.decision__form { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-md); padding: 12px 12px 4px; margin-bottom: 12px; }
.decision__form :deep(.ui-field) { margin-bottom: 12px; }
.owner { display: flex; align-items: flex-start; gap: 10px; padding-top: 10px; border-top: 1px solid var(--c-separator); cursor: pointer; }
.owner .b { display: block; } .owner .small { display: block; }
/* the Approve button, not yet enabled: a faded version of itself, not dead grey */
.decision .ui-btn.is-waiting:disabled { background: color-mix(in srgb, var(--c-action) 14%, var(--c-surface)); color: var(--c-action-text); box-shadow: none; }
.caption { display: flex; align-items: center; gap: 6px; margin: 8px 2px 12px; font-size: var(--fs-xs); }
.caption.ok { color: var(--c-ok-text); } .caption.ok .ui-icon { color: var(--c-ok); }
.caption.dim { color: var(--c-text-3); } .caption.dim .ui-icon { color: var(--c-text-3); }
/* Reject: quiet, never competes with Approve */
.reject { color: var(--c-text-2); }
.reject:hover:not(:disabled) { background: var(--c-bad-bg); color: var(--c-bad-text); }
.cmt { margin-top: 12px; }
.cmt :deep(label) { color: var(--c-action-text); }
/* phones: keep the decision in reach while scrolling the evidence */
@media (max-width: 640px) { .decision { position: sticky; bottom: 0; z-index: 2; } }
.alt { display: flex; gap: 10px; align-items: flex-start; padding: 10px 12px; border-radius: var(--radius-md); cursor: pointer; margin-top: 6px; background: var(--c-fill); }
.alt.sel { background: var(--c-primary-tint); box-shadow: inset 0 0 0 1px var(--c-primary); }
.alt.blocked { opacity: 0.6; cursor: not-allowed; }
.alt input { margin-top: 4px; }
.block { display: block; }
.kv { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 6px 10px; font-size: 14px; margin-bottom: 0; }
.kv dt { color: var(--c-text-2); } .kv dd { margin: 0; }
</style>
