<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute } from "vue-router";
import BaseBadge from "@/components/common/BaseBadge.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
import type { ActionCandidate, IncidentStep } from "@/types/api";
import { duration, time, titleCase } from "@/utils/format";
const route = useRoute(),
  ui = useUiStore(),
  id = Number(route.params.id);
const state = useAsyncState(() => api.incident(id), 4000);
const selected = ref(0),
  ownerConfirmed = ref(false),
  approver = ref(localStorage.getItem("approver") || ""),
  comment = ref(""),
  score = ref(0),
  rcaCorrect = ref(true),
  feedback = ref(""),
  busy = ref("");
watch(
  () => state.data?.score,
  (v) => {
    if (v && !score.value) score.value = v;
  },
  { immediate: true },
);
watch(
  () => state.data?.feedback,
  (v) => {
    if (v && !feedback.value) feedback.value = v;
  },
  { immediate: true },
);
watch(
  () => state.data?.rca_correct,
  (v) => {
    if (v != null) rcaCorrect.value = v !== 0;
  },
  { immediate: true },
);
const waiting = computed(() =>
  ["awaiting_approval", "remediation_failed"].includes(
    state.data?.status || "",
  ),
);
const investigating = computed(() =>
  ["open", "analyzing"].includes(state.data?.status || ""),
);
const candidates = computed(() => state.data?.candidates || []);
const action = computed<ActionCandidate>(
  () => candidates.value[selected.value] || state.data?.action || {},
);
const dryRun = computed(() => action.value.dry_run || state.data?.dry_run);
const canApprove = computed(
  () =>
    !!approver.value.trim() &&
    ownerConfirmed.value &&
    dryRun.value?.ok !== false,
);
const statusTone = computed<"success" | "danger" | "ai" | "warning">(() =>
  state.data?.status === "resolved"
    ? "success"
    : state.data?.status === "awaiting_approval"
      ? "ai"
      : state.data?.status === "remediation_failed"
        ? "danger"
        : "warning",
);
async function mutate(label: string, run: () => Promise<unknown>) {
  busy.value = label;
  try {
    await run();
    ui.notify(label);
    await state.load();
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Action failed");
  } finally {
    busy.value = "";
  }
}
function approve() {
  if (!canApprove.value) return;
  localStorage.setItem("approver", approver.value);
  void mutate("Fix approved", () =>
    api.approveIncident(id, {
      approver: approver.value.trim(),
      action_index: selected.value,
      comment: comment.value,
      owner_confirmed: true,
    }),
  );
}
function reject() {
  void mutate("Problem rejected", () =>
    api.rejectIncident(id, {
      approver: approver.value.trim() || "owner",
      comment: comment.value,
    }),
  );
}
function close() {
  void mutate("Problem closed", () => api.closeIncident(id));
}
function reanalyze() {
  void mutate("Analysis restarted", () => api.reanalyzeIncident(id));
}
function sendFeedback() {
  if (!score.value) return ui.notify("Choose a star rating first");
  void mutate("Feedback saved", () =>
    api.feedback(id, {
      score: score.value,
      rca_correct: rcaCorrect.value,
      comment: feedback.value,
    }),
  );
}
function stepDetail(step: IncidentStep) {
  return (
    step.output ??
    (step.checks
      ? { checks: step.checks, changes: step.changes, impact: step.impact }
      : step.facts
        ? { facts: step.facts, candidates: step.candidates }
        : null)
  );
}
const execution = computed(
  () => state.data?.execution as Record<string, any> | undefined,
);
</script>
<template>
  <div class="page">
    <LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><template v-else-if="state.data"
      ><RouterLink class="back" to="/problems">‹ Problems</RouterLink
      ><PageHeader
        :title="state.data.title"
        :description="`${state.data.entity_type === 'host' ? 'Computer' : 'Service'} ${state.data.entity} · detected ${time(state.data.detected_at)} · owner ${state.data.owner || '—'}`"
        ><BaseBadge
          :tone="state.data.severity === 'critical' ? 'danger' : 'warning'"
          >{{ titleCase(state.data.severity) }}</BaseBadge
        ><BaseBadge :tone="statusTone">{{
          titleCase(state.data.status)
        }}</BaseBadge></PageHeader
      >
      <div class="stepper">
        <div
          v-for="(step, index) in [
            { n: 'Detected', t: state.data.detected_at },
            { n: 'Analyzed', t: state.data.analyzed_at },
            { n: 'Approved', t: state.data.approved_at },
            { n: 'Fixed', t: execution?.result?.ok ? execution?.ts : null },
            {
              n: 'Verified',
              t:
                state.data.status === 'resolved'
                  ? state.data.resolved_at
                  : null,
            },
          ]"
          :key="step.n"
          :class="{ done: step.t, now: !step.t && index === 0 }"
        >
          <i>{{ step.t ? "✓" : index + 1 }}</i
          ><b>{{ step.n }}</b
          ><small>{{ time(step.t) }}</small>
        </div>
      </div>
      <div class="split">
        <div class="stack">
          <BasePanel title="What happened"
            ><template v-if="state.data.root_cause"
              ><h3 class="cause">{{ state.data.root_cause }}</h3>
              <p class="muted">{{ state.data.summary }}</p>
              <div class="confidence">
                <span>AI confidence</span
                ><i
                  ><b
                    :style="{
                      width: `${(state.data.confidence || 0) * 100}%`,
                    }" /></i
                ><strong
                  >{{ Math.round((state.data.confidence || 0) * 100) }}%</strong
                >
              </div>
              <small class="dim"
                >{{
                  state.data.path === "known"
                    ? "Matched runbook memory"
                    : `Written by ${state.data.llm_model || "AI"}`
                }}
                · analysis took
                {{ duration((state.data.analysis_ms || 0) / 1000) }}</small
              ></template
            >
            <div v-else class="investigating">
              AI is reading metrics, traces, and logs…
            </div></BasePanel
          ><BasePanel v-if="state.data.evidence?.length" title="Evidence"
            ><div v-for="e in state.data.evidence" :key="e" class="evidence">
              {{ e }}
            </div></BasePanel
          ><BasePanel v-if="state.data.runbook?.length" title="Runbook"
            ><ol>
              <li v-for="line in state.data.runbook" :key="line">{{ line }}</li>
            </ol></BasePanel
          >
          <details class="investigation">
            <summary>
              How the AI investigated ·
              {{ state.data.steps?.length || 0 }} steps
            </summary>
            <div
              v-for="(step, index) in state.data.steps"
              :key="index"
              class="timeline"
            >
              <i />
              <div>
                <b>{{
                  step.kind === "tool" ? `${step.title}()` : step.title
                }}</b>
                <p v-if="step.detail">{{ step.detail }}</p>
                <details v-if="stepDetail(step)">
                  <summary>Details</summary>
                  <pre>{{ JSON.stringify(stepDetail(step), null, 2) }}</pre>
                </details>
              </div>
              <small>{{
                step.ms != null ? `${(step.ms / 1000).toFixed(1)}s` : ""
              }}</small>
            </div>
          </details>
        </div>
        <aside class="stack">
          <BasePanel title="Recommended fix"
            ><div v-if="investigating" class="investigating">
              The AI is investigating ·
              {{ state.data.steps?.length || 0 }} steps so far
            </div>
            <template v-else-if="waiting"
              ><div v-if="candidates.length > 1" class="options">
                <label
                  v-for="(candidate, index) in candidates"
                  :key="index"
                  :class="{
                    selected: selected === index,
                    blocked: candidate.dry_run?.ok === false,
                  }"
                  ><input
                    v-model="selected"
                    type="radio"
                    :value="index"
                    :disabled="candidate.dry_run?.ok === false"
                  /><span
                    ><b>{{ candidate.label }}</b
                    ><small
                      >{{ index === 0 ? "Recommended · " : ""
                      }}{{
                        candidate.dry_run?.ok === false
                          ? "Dry run failed"
                          : "Dry run passed"
                      }}</small
                    ></span
                  ></label
                >
              </div>
              <div class="fix">
                <small>{{
                  selected === 0 ? "AI recommends" : "You selected"
                }}</small
                ><strong>{{ action.label || "No action available" }}</strong>
              </div>
              <p>
                Dry run
                <b :class="dryRun?.ok ? 'success-text' : 'danger-text'">{{
                  dryRun?.ok ? "passed" : "failed"
                }}</b>
                · nothing changed yet
              </p>
              <div
                v-for="check in dryRun?.checks"
                :key="check.name"
                class="check"
                :class="check.ok ? 'success-text' : 'danger-text'"
              >
                {{ check.ok ? "✓" : "×" }}
                <span
                  >{{ check.name }}<small>{{ check.detail }}</small></span
                >
              </div>
              <details v-if="dryRun?.changes?.length">
                <summary>
                  What will change ({{ dryRun.changes.length }})
                </summary>
                <pre>{{ dryRun.changes.join("\n") }}</pre>
              </details>
              <p v-if="dryRun?.impact">
                <span class="muted">Impact:</span> {{ dryRun.impact }}
              </p>
              <label class="owner"
                ><span
                  ><b>I'm the owner</b
                  ><small
                    >{{ state.data.owner || "unassigned" }} approves this
                    fix</small
                  ></span
                ><input v-model="ownerConfirmed" type="checkbox" /></label
              ><BaseInput
                v-model="approver"
                label="Your name"
                placeholder="e.g. Napat"
              /><BaseInput v-model="comment" label="Comment (optional)" />
              <div class="actions">
                <BaseButton variant="danger" :disabled="!!busy" @click="reject"
                  >Reject</BaseButton
                ><BaseButton
                  :disabled="!canApprove || !!busy"
                  @click="approve"
                  >{{ busy || "Approve fix" }}</BaseButton
                >
              </div></template
            ><template v-else
              ><div class="fix">
                <small>Selected action</small
                ><strong>{{
                  execution?.action?.label ||
                  state.data.action?.label ||
                  "No action"
                }}</strong>
              </div>
              <dl>
                <template v-if="execution?.approver"
                  ><dt>Approved by</dt>
                  <dd>{{ execution.approver }}</dd></template
                ><template v-if="execution?.result"
                  ><dt>Result</dt>
                  <dd>{{ execution.result.detail }}</dd></template
                ><template v-if="execution?.verification"
                  ><dt>Verified</dt>
                  <dd>
                    {{
                      execution.verification.healthy
                        ? "Metrics back to normal"
                        : "Still abnormal"
                    }}
                  </dd></template
                >
              </dl></template
            ></BasePanel
          ><BasePanel title="Rate this analysis"
            ><div class="stars">
              <button
                v-for="n in 5"
                :key="n"
                :class="{ on: n <= score }"
                :aria-label="`${n} stars`"
                @click="score = n"
              >
                ★
              </button>
            </div>
            <label class="owner"
              ><span>Root cause was correct</span
              ><input v-model="rcaCorrect" type="checkbox" /></label
            ><label class="label">What should the AI learn?</label
            ><textarea v-model="feedback" class="field" rows="3" /><BaseButton
              variant="secondary"
              :disabled="!!busy"
              @click="sendFeedback"
              >Send feedback</BaseButton
            ></BasePanel
          ><BasePanel title="Notifications"
            ><div
              v-for="n in state.data.notifications"
              :key="n.id"
              class="notice"
            >
              {{ titleCase(n.event) }} · {{ time(n.ts) }} · {{ n.status }}
            </div>
            <p v-if="!state.data.notifications?.length" class="muted">
              None sent
            </p>
            <div class="actions">
              <BaseButton
                v-if="state.data.status !== 'analyzing'"
                variant="ghost"
                :disabled="!!busy"
                @click="reanalyze"
                >Run analysis again</BaseButton
              ><BaseButton
                v-if="
                  !['resolved', 'closed', 'rejected'].includes(
                    state.data.status,
                  )
                "
                variant="ghost"
                :disabled="!!busy"
                @click="close"
                >Close problem</BaseButton
              >
            </div></BasePanel
          >
        </aside>
      </div></template
    >
  </div>
</template>
<style scoped>
.back {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--color-accent-primary);
}
.stepper {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  margin: 4px 0 20px;
}
.stepper > div {
  position: relative;
  display: grid;
  justify-items: center;
  color: var(--color-text-dim);
  font-size: 11px;
}
.stepper > div:before {
  position: absolute;
  z-index: 0;
  top: 13px;
  left: -50%;
  width: 100%;
  height: 2px;
  background: var(--color-border-default);
  content: "";
}
.stepper > div:first-child:before {
  display: none;
}
.stepper i {
  z-index: 1;
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-surface-subtle);
  font-style: normal;
}
.stepper .done {
  color: var(--color-status-success-text);
}
.stepper .done i {
  background: var(--color-status-success-bg);
}
.stepper b {
  margin-top: 4px;
}
.split {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 1fr);
  gap: 16px;
}
.stack {
  display: grid;
  gap: 16px;
  align-content: start;
}
.cause {
  margin: 0;
}
.confidence {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 12px 0;
}
.confidence > i {
  width: 160px;
  height: 7px;
  border-radius: 5px;
  background: var(--color-surface-subtle);
}
.confidence > i b {
  display: block;
  height: 100%;
  border-radius: 5px;
  background: var(--color-accent-ai);
}
.evidence {
  border-left: 3px solid var(--color-accent-primary);
  padding: 7px 10px;
}
.investigating {
  border-radius: 8px;
  background: var(--color-status-ai-bg);
  color: var(--color-status-ai-text);
  padding: 14px;
}
.investigation {
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: white;
  padding: 14px;
}
.investigation > summary {
  cursor: pointer;
  font-weight: 600;
}
.timeline {
  display: grid;
  grid-template-columns: 10px 1fr auto;
  gap: 10px;
  border-bottom: 1px solid var(--color-border-default);
  padding: 12px 0;
}
.timeline > i {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--color-accent-ai);
}
.timeline p {
  margin: 3px 0;
  color: var(--color-text-muted);
}
pre {
  overflow: auto;
  border-radius: 6px;
  background: #101827;
  color: #dbeafe;
  padding: 10px;
  font-size: 11px;
}
.fix {
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  background: var(--color-status-ai-bg);
  padding: 12px;
}
.fix strong {
  font-size: 16px;
}
.options {
  display: grid;
  gap: 7px;
  margin-bottom: 10px;
}
.options label {
  display: flex;
  gap: 8px;
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  padding: 9px;
}
.options label.selected {
  border-color: var(--color-accent-ai);
}
.options label.blocked {
  opacity: 0.55;
}
.options span,
.owner span {
  display: flex;
  flex-direction: column;
}
.options small,
.owner small,
.check small {
  display: block;
  color: var(--color-text-muted);
}
.check {
  display: flex;
  gap: 8px;
  padding: 5px 0;
}
.owner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--color-border-default);
  border-bottom: 1px solid var(--color-border-default);
  margin: 12px 0;
  padding: 10px 0;
}
.actions {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}
.stars button {
  border: 0;
  background: transparent;
  color: var(--color-border-strong);
  font-size: 28px;
  cursor: pointer;
}
.stars button.on {
  color: var(--color-accent-highlight);
}
.notice {
  border-bottom: 1px solid var(--color-border-default);
  padding: 5px 0;
  font-size: 12px;
}
dl {
  display: grid;
  grid-template-columns: 100px 1fr;
  font-size: 12px;
}
dt {
  color: var(--color-text-muted);
}
dd {
  margin: 0;
}
@media (max-width: 900px) {
  .split {
    grid-template-columns: 1fr;
  }
  .stepper small {
    display: none;
  }
}
</style>
