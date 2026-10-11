<script setup>
import { ref } from "vue";
import { api } from "@/lib/api";
import { useUiStore } from "@/stores/ui";
const ui = useUiStore();
const d = ref(null);
const s = ref({});
api.settings.get().then((r) => { d.value = r; s.value = { ...r.settings }; });
// used only until a host or service has a few hours of history (see "What is normal" below)
const FALLBACK = [["err_threshold", "Error rate", "0.05 = 5% of requests"], ["p95_threshold_ms", "Response time p95 (ms)"], ["cpu_threshold", "CPU %"],
  ["mem_threshold", "Memory %"], ["disk_threshold", "Disk %"]];
const SENSITIVITY = [{ value: "low", label: "Fewer alerts" }, { value: "normal", label: "Balanced" }, { value: "high", label: "Catch more" }];
const SENS_HINT = { low: "Only clear breaks from normal. Quietest, may notice a slow problem later.",
  normal: "Recommended. Ignores everyday wobble, raises real changes.",
  high: "Small changes from normal are raised too. Expect more incidents." };
// mirrors the safety limits in aiops-api/app/baseline.py
const ALWAYS = ["Disk 95% full or more", "Memory 97% or more", "20% of requests failing or more", "A server stops reporting"];
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
      <router-link to="/design" class="small">See the design system</router-link>
    </UiCard>
    <div class="section-label row"><UiLogo name="teams" :size="16" />Microsoft Teams</div>
    <UiCard>
      <UiField v-model="s.teams_webhook" label="Teams link (Incoming Webhook or Workflow URL)" placeholder="https://...webhook.office.com/..." />
      <p class="small muted mt-2">Owners get a card when an incident is found, when a fix needs approval, and when it is resolved.</p>
      <UiButton variant="tint" size="sm" class="mt-2" @click="testTeams">Send a test message</UiButton>
    </UiCard>
    <div class="section-label">AI</div>
    <UiList>
      <UiListRow title="Model" subtitle="Runs on this server's CPU. Bigger models are slower.">
        <template #leading><UiAppTile logo="ollama" /></template>
        <template #accessory><select v-model="s.llm_model" class="sel" aria-label="Model"><option v-for="m in d.llm.models || [s.llm_model]" :key="m">{{ m }}</option></select></template></UiListRow>
      <UiListRow title="Investigate new incidents automatically">
        <template #leading><UiAppTile icon="sparkle" color="var(--c-ai)" /></template>
        <template #accessory><UiSwitch :model-value="s.auto_analyze === '1'" label="Investigate automatically" @update:model-value="(v) => (s.auto_analyze = v ? '1' : '0')" /></template></UiListRow>
    </UiList>
    <div class="section-label">When to raise an incident</div>
    <UiCard>
      <p>AIOps learns what is normal for each host and each service at each time of day, from its own history.
        An incident is raised when a metric leaves its normal range for a while, up or down.</p>
      <ul class="small muted rules">
        <li>A server that always runs at 90% CPU is fine. The same server dropping to 5% is raised: its work has stopped.</li>
        <li>A service that usually fails 8% of requests is judged against 8%, not against a single number for every service.</li>
        <li>Traffic that suddenly disappears is raised, because nobody complains when a page silently stops being used.</li>
      </ul>
      <div class="sens">
        <span class="b">Sensitivity</span>
        <UiSegmented v-model="s.sensitivity" label="Sensitivity" :options="SENSITIVITY" />
      </div>
      <p class="small muted mt-2">{{ SENS_HINT[s.sensitivity || "normal"] }}</p>
    </UiCard>
    <UiCard class="mt" title="Always raised, whatever is normal">
      <ul class="always"><li v-for="a in ALWAYS" :key="a">{{ a }}</li></ul>
    </UiCard>
    <UiDisclosure class="mt" title="Limits used while a new host or service is still being learned" meta="first few hours">
      <p class="small muted">A metric needs about three hours of history before AIOps knows its normal range. Until then these fixed limits apply.</p>
      <div class="grid grid--2"><UiField v-for="[k, l, h] in FALLBACK" :key="k" v-model="s[k]" :label="l" :hint="h" /></div>
    </UiDisclosure>
    <div class="section-label">Security and verification</div>
    <UiCard><div class="grid grid--2">
      <UiField v-model="s.auth_fail_per_min" label="Failed logins per minute" hint="raised as a password attack" />
      <UiField v-model="s.verify_after_s" label="Check the fix after (seconds)" />
    </div></UiCard>
    <div class="section-label">Discovery</div>
    <UiCard><UiField v-model="s.discovery_ignore_containers" label="Containers that belong to the platform (not shown as services)" mono /></UiCard>
    <UiButton class="mt" @click="save">Save</UiButton>
  </div>
</template>
<style scoped>
.sel { background: var(--c-fill); border: 0; border-radius: var(--radius-sm); padding: 6px 10px; }
.section-label.row { display: flex; gap: 6px; }
.rules { margin: 10px 0 0; padding-left: 18px; } .rules li { margin: 4px 0; }
.sens { display: flex; align-items: center; gap: 14px; margin-top: 16px; flex-wrap: wrap; }
.b { font-weight: var(--fw-semibold); }
.always { margin: 0; padding-left: 18px; } .always li { margin: 3px 0; }
</style>
