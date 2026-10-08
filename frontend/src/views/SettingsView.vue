<script setup>
import { ref } from "vue";
import { api } from "@/lib/api";
import { useUiStore } from "@/stores/ui";
const ui = useUiStore();
const d = ref(null);
const s = ref({});
api.settings.get().then((r) => { d.value = r; s.value = { ...r.settings }; });
const THRESHOLDS = [["err_threshold", "Error rate", "0.05 = 5% of requests"], ["p95_threshold_ms", "Response time p95 (ms)"], ["cpu_threshold", "CPU %"],
  ["mem_threshold", "Memory %"], ["disk_threshold", "Disk %"], ["auth_fail_per_min", "Failed logins per minute"], ["verify_after_s", "Check the fix after (seconds)"]];
async function save() {
  try { await api.settings.update(s.value); ui.toast("Saved"); } catch (e) { ui.toast(e.message); }
}
async function testTeams() {
  await save();
  const r = await api.notifications.test();
  ui.toast(`Teams: ${r.status}`);
}
</script>
<template>
  <div v-if="d" class="page page--narrow">
    <UiPageHeader title="Settings" />
    <div class="section-label">Appearance</div>
    <UiCard>
      <UiSegmented :model-value="ui.prefs.theme || 'auto'" label="Appearance" @update:model-value="ui.setTheme"
                   :options="[{ value: 'auto', label: 'Auto', icon: 'dark_theme' }, { value: 'light', label: 'Light', icon: 'weather_sunny' }, { value: 'dark', label: 'Dark', icon: 'weather_moon' }]" />
      <p class="small muted mt-2">Auto follows your computer's light or dark setting. Saved in this browser only.</p>
    </UiCard>
    <div class="section-label row"><UiLogo name="teams" :size="16" />Microsoft Teams</div>
    <UiCard>
      <UiField v-model="s.teams_webhook" label="Teams link (Incoming Webhook or Workflow URL)" placeholder="https://...webhook.office.com/..." />
      <p class="small muted mt-2">Owners get a card when a problem is found, when a fix needs approval, and when it is resolved.</p>
      <UiButton variant="tint" size="sm" class="mt-2" @click="testTeams">Send a test message</UiButton>
    </UiCard>
    <div class="section-label">AI</div>
    <UiList>
      <UiListRow title="Model" subtitle="Runs on this server's CPU. Bigger models are slower.">
        <template #leading><UiAppTile logo="ollama" /></template>
        <template #accessory><select v-model="s.llm_model" class="sel" aria-label="Model"><option v-for="m in d.llm.models || [s.llm_model]" :key="m">{{ m }}</option></select></template></UiListRow>
      <UiListRow title="Investigate new problems automatically">
        <template #leading><UiAppTile icon="sparkle" color="var(--c-ai)" /></template>
        <template #accessory><UiSwitch :model-value="s.auto_analyze === '1'" label="Investigate automatically" @update:model-value="(v) => (s.auto_analyze = v ? '1' : '0')" /></template></UiListRow>
    </UiList>
    <div class="section-label">When to raise a problem</div>
    <UiCard><div class="grid grid--2"><UiField v-for="[k, l, h] in THRESHOLDS" :key="k" v-model="s[k]" :label="l" :hint="h" /></div></UiCard>
    <div class="section-label">Discovery</div>
    <UiCard><UiField v-model="s.discovery_ignore_containers" label="Containers that belong to the platform (not shown as services)" mono /></UiCard>
    <UiButton class="mt" @click="save">Save</UiButton>
  </div>
</template>
<style scoped>
.sel { background: var(--c-fill); border: 0; border-radius: var(--radius-sm); padding: 6px 10px; }
.section-label.row { display: flex; gap: 6px; }
</style>
