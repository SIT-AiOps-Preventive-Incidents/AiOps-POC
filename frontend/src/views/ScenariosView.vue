<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "@/lib/api";
import { useUiStore } from "@/stores/ui";
const ui = useUiStore();
const router = useRouter();
const busy = ref("");
const SCEN = [
  { id: "bad_deploy", icon: "warning", title: "Bad release", what: "A new payment release (v1.3.0) has a bug. About half of all payments fail.", ai: "finds the bad commit and proposes a rollback to the last good version." },
  { id: "instance_fault", icon: "server", title: "One server behind the load balancer breaks", what: "frontend-b loses its cache; frontend-a stays fine.", ai: "reads the load balancer logs and restarts only frontend-b." },
  { id: "slow_db", icon: "clock", title: "Slow database", what: "Inventory queries take 1.6 s and the connection pool fills up.", ai: "finds where the time goes and proposes restarting inventory." },
  { id: "cpu_hog", icon: "developer_board", title: "Runaway job", what: "A batch job eats 3 CPU cores on the server.", ai: "finds the container using the CPU and proposes a restart." },
  { id: "brute_force", icon: "shield", title: "Password attack", what: "One IP tries hundreds of passwords through the firewall.", ai: "confirms it in the firewall and app logs, then proposes blocking the IP." },
];
async function run(id) {
  busy.value = id;
  try {
    await api.scenarios.run(id);
    ui.toast(id === "reset" ? "Everything reset" : "Started. Opening Problems...");
    if (id !== "reset") setTimeout(() => router.push("/problems"), 900);
  } catch (e) { ui.toast(e.message); } finally { busy.value = ""; }
}
</script>
<template>
  <div class="page">
    <UiPageHeader title="Demo Scenarios" subtitle="Break something on purpose and watch the AI find and fix it. Detection takes about 40 s, the AI another 1-3 minutes." />
    <UiList>
      <UiListRow v-for="s in SCEN" :key="s.id" :title="s.title" :detail="`${s.what} The AI ${s.ai}`">
        <template #leading><UiAppTile :icon="s.icon" color="var(--c-warn)" /></template>
        <template #accessory><UiButton size="sm" :loading="busy === s.id" @click="run(s.id)">Start</UiButton></template>
      </UiListRow>
    </UiList>
    <UiList class="mt"><UiListRow title="Reset everything" subtitle="Clears injected faults, the attack and the firewall block list">
      <template #leading><UiAppTile icon="arrow_sync" color="var(--c-neutral)" /></template>
      <template #accessory><UiButton variant="tint" size="sm" :loading="busy === 'reset'" @click="run('reset')">Reset</UiButton></template></UiListRow></UiList>
  </div>
</template>
