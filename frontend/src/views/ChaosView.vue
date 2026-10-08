<script setup lang="ts">
import { useRouter } from "vue-router";
import AppIcon from "@/components/common/AppIcon.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
const router = useRouter(),
  ui = useUiStore();
const scenarios = [
  [
    "bad_deploy",
    "Bad release",
    "warning",
    "A new payment release has a bug. About half of payments fail.",
    "finds the bad commit and proposes a rollback.",
  ],
  [
    "instance_fault",
    "One server breaks",
    "server",
    "frontend-b loses its cache while frontend-a stays healthy.",
    "isolates and restarts only the failing instance.",
  ],
  [
    "slow_db",
    "Slow database",
    "clock",
    "Inventory queries take 1.6 seconds and the pool fills up.",
    "finds the bottleneck and proposes a restart.",
  ],
  [
    "cpu_hog",
    "Runaway job",
    "developer_board",
    "A batch job consumes three CPU cores.",
    "finds the container and proposes a restart.",
  ],
  [
    "brute_force",
    "Password attack",
    "shield",
    "One IP tries hundreds of passwords.",
    "correlates firewall and app logs, then proposes blocking it.",
  ],
] as const;
let busy = "";
async function run(id: string) {
  busy = id;
  try {
    await api.chaos(id);
    ui.notify(id === "reset" ? "Everything reset" : "Scenario started");
    if (id !== "reset") window.setTimeout(() => router.push("/problems"), 900);
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Could not start scenario");
  } finally {
    busy = "";
  }
}
</script>
<template>
  <div class="page">
    <PageHeader
      title="Chaos Scenarios"
      description="Break something on purpose and watch the AI detect, investigate, and propose a safe fix."
    />
    <div class="scenarios">
      <BasePanel v-for="s in scenarios" :key="s[0]"
        ><div class="scenario">
          <AppIcon :name="s[2]" set="fluent" :size="22" /><span
            ><b>{{ s[1] }}</b>
            <p>{{ s[3] }} The AI {{ s[4] }}</p></span
          ><BaseButton :disabled="!!busy" @click="run(s[0])">{{
            busy === s[0] ? "Starting…" : "Start"
          }}</BaseButton>
        </div></BasePanel
      ><BasePanel
        ><div class="scenario">
          <AppIcon name="wrench" set="fluent" :size="22" /><span
            ><b>Reset everything</b>
            <p>
              Clear injected faults, attack traffic, and the firewall block
              list.
            </p></span
          ><BaseButton
            variant="secondary"
            :disabled="!!busy"
            @click="run('reset')"
            >Reset</BaseButton
          >
        </div></BasePanel
      >
    </div>
  </div>
</template>
<style scoped>
.scenarios {
  display: grid;
  gap: 10px;
}
.scenario {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: 12px;
}
.scenario p {
  margin: 3px 0;
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
