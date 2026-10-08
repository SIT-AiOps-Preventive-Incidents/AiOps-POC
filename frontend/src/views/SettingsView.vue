<script setup lang="ts">
import { reactive, ref } from "vue";
import AppIcon from "@/components/common/AppIcon.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import StatusChip from "@/components/common/StatusChip.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
const ui = useUiStore(),
  form = reactive<Record<string, string>>({}),
  busy = ref("");
const state = useAsyncState(async () => {
  const d = await api.settings();
  Object.assign(form, d.settings);
  return d;
});
const fields = [
  ["err_threshold", "Error rate", "0.05 = 5% of requests"],
  ["p95_threshold_ms", "Response time p95 (ms)", ""],
  ["cpu_threshold", "CPU %", ""],
  ["mem_threshold", "Memory %", ""],
  ["disk_threshold", "Disk %", ""],
  ["auth_fail_per_min", "Failed logins per minute", ""],
] as const;
async function save(silent = false) {
  busy.value = "save";
  try {
    await api.saveSettings({ ...form });
    if (!silent) ui.notify("Settings saved");
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Could not save settings");
    throw e;
  } finally {
    busy.value = "";
  }
}
async function test() {
  try {
    await save(true);
    busy.value = "test";
    const result = await api.testTeams();
    ui.notify(`Teams: ${result.status}`);
  } catch {
  } finally {
    busy.value = "";
  }
}
</script>
<template>
  <div class="page settings">
    <PageHeader title="Settings" /><LoadingState
      v-if="state.loading && !state.data"
    /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><template v-else-if="state.data"
      ><BasePanel
        ><template #header
          ><h2 class="section-title">
            <AppIcon name="teams" set="brand" :size="20" /> Microsoft Teams
          </h2>
          <StatusChip :tone="form.teams_webhook ? 'success' : 'neutral'">{{
            form.teams_webhook ? "Configured" : "Not configured"
          }}</StatusChip></template
        ><BaseInput
          v-model="form.teams_webhook"
          label="Teams link (Incoming Webhook or Workflow URL)"
          placeholder="https://...webhook.office.com/..."
        />
        <p class="muted">
          Owners receive cards when a problem is detected, needs approval, and
          is resolved.
        </p>
        <BaseButton variant="secondary" :disabled="!!busy" @click="test">{{
          busy === "test" ? "Sending…" : "Send a test message"
        }}</BaseButton></BasePanel
      ><BasePanel
        ><template #header
          ><h2 class="section-title">
            <AppIcon name="ollama" set="brand" :size="20" /> AI
          </h2>
          <StatusChip :tone="state.data.llm.up ? 'success' : 'danger'">{{
            state.data.llm.up ? "Online" : "Offline"
          }}</StatusChip></template
        ><label class="input"
          ><span class="label">Model</span
          ><select v-model="form.llm_model" class="field">
            <option v-for="model in state.data.llm.models" :key="model">
              {{ model }}
            </option>
          </select></label
        ><label class="toggle"
          ><span
            ><b>Investigate new problems automatically</b
            ><small
              >Start the agentic RCA workflow as soon as a signal is
              detected.</small
            ></span
          ><input
            type="checkbox"
            :checked="form.auto_analyze === '1'"
            @change="
              form.auto_analyze = ($event.target as HTMLInputElement).checked
                ? '1'
                : '0'
            " /></label
        ><BaseInput
          v-model="form.verify_after_s"
          label="Check the fix after (seconds)"
          type="number" /></BasePanel
      ><BasePanel title="When to raise a problem"
        ><div class="thresholds">
          <BaseInput
            v-for="f in fields"
            :key="f[0]"
            v-model="form[f[0]]"
            :label="f[1]"
            :placeholder="f[2]"
            type="number"
            step="any"
          /></div></BasePanel
      ><BaseButton :disabled="!!busy" @click="save()">{{
        busy === "save" ? "Saving…" : "Save settings"
      }}</BaseButton></template
    >
  </div>
</template>
<style scoped>
.settings {
  max-width: 820px;
}
.settings > :deep(.panel) + :deep(.panel) {
  margin-top: 16px;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--color-border-default);
  border-bottom: 1px solid var(--color-border-default);
  margin: 14px 0;
  padding: 12px 0;
}
.toggle span {
  display: flex;
  flex-direction: column;
}
.toggle small {
  color: var(--color-text-muted);
}
.thresholds {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}
.settings > :deep(.button) {
  margin-top: 16px;
}
@media (max-width: 620px) {
  .thresholds {
    grid-template-columns: 1fr;
  }
}
</style>
