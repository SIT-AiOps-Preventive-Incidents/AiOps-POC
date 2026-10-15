<script setup>
import { computed, onMounted, ref } from "vue";
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
// Offered only while the network lab (netlab/) runs; they show up on the Network page first.
const NET = [
  { id: "net_link_down", icon: "flowchart", title: "Uplink cut", what: "The cable between sw-data and the core router goes down. payment and inventory lose their path to checkout.", ai: "sees the link go down on the Network page, which services sit behind it, and checkout's errors on Incidents." },
  { id: "net_host_port", icon: "developer_board", title: "Server port down", what: "sw-data's port toward the payment and inventory servers goes down.", ai: "marks both servers down on the map and names the switch port." },
  { id: "net_rogue_device", icon: "shield", title: "Unknown device plugged in", what: "A device nobody registered joins the app network and starts talking.", ai: "flags it as an unknown asset on the switch port where it appeared." },
];
const netAvailable = ref([]);
const listed = ref(null);   // null until loaded: show the shop list meanwhile
onMounted(async () => {
  try {
    listed.value = await api.scenarios.list();
    netAvailable.value = listed.value.filter((id) => id.startsWith("net_"));
  } catch { netAvailable.value = []; }
});
const shopScen = computed(() => (listed.value ? SCEN.filter((s) => listed.value.includes(s.id)) : SCEN));

// AnoMod (MSR'26): incidents recorded on a real SocialNetwork deployment, replayed live. The case name says what broke.
const SVC = { Media: "media", MediaService: "media", SocialGraph: "social-graph", UserTimeline: "user-timeline",
  HomeTimeline: "home-timeline", TextService: "text", UserService: "user" };
function describe(id) {
  const c = id.slice("anomod:".length);
  const [kind, ...rest] = c.split("_");
  const svc = SVC[rest[rest.length - 1]] || rest.join(" ");
  if (kind === "Perf") return { icon: "developer_board", title: `Resource fault: ${rest.join(" ").toLowerCase()}`, what: "The machine under SocialNetwork runs out of a resource while users keep posting and reading." };
  if (kind === "Svc") return { icon: "server", title: `${svc}-service killed`, what: `The ${svc}-service container is killed mid-traffic and comes back.` };
  if (kind === "DB") return { icon: "database", title: `${svc} cache capped`, what: `The Redis cache behind ${svc}-service is limited, so lookups miss and fall through.` };
  if (kind === "Code") return { icon: "code", title: `${svc}-service stops answering`, what: `A code-level fault stops ${svc}-service; its callers start failing.` };
  return { icon: "warning", title: c.replace(/_/g, " "), what: "A recorded fault." };
}
const anomod = computed(() => (listed.value || []).filter((id) => id.startsWith("anomod:")).map((id) => ({ id, ...describe(id) })));
async function run(id) {
  busy.value = id;
  try {
    await api.scenarios.run(id);
    ui.toast(id === "reset" ? "Everything reset" : id.startsWith("net_") ? "Started. Opening Fleet…" : "Started. Opening Incidents…");
    if (id !== "reset") setTimeout(() => router.push(id.startsWith("net_") ? "/network" : "/problems"), 900);
  } catch (e) { ui.toast(e.message); } finally { busy.value = ""; }
}
</script>
<template>
  <div class="page">
    <UiPageHeader title="Demo scenarios" subtitle="Break something on purpose and watch the AI find and fix it. Detection takes about 40 s, the AI another 1-3 minutes." />
    <template v-if="anomod.length">
      <h3 class="sec sec--first">SocialNetwork (AnoMod, recorded on a real deployment)</h3>
      <p class="small muted note">Each run replays the logs and traces AnoMod recorded while the fault was injected, re-timed to now. Detection and root cause come from RadarOps, not from the recording.</p>
      <UiList>
        <UiListRow v-for="s in anomod" :key="s.id" :title="s.title" :detail="s.what">
          <template #leading><UiAppTile :icon="s.icon" color="var(--c-warn)" /></template>
          <template #accessory><UiButton size="sm" :loading="busy === s.id" @click="run(s.id)">Start</UiButton></template>
        </UiListRow>
      </UiList>
    </template>
    <UiList v-if="shopScen.length">
      <UiListRow v-for="s in shopScen" :key="s.id" :title="s.title" :detail="`${s.what} The AI ${s.ai}`">
        <template #leading><UiAppTile :icon="s.icon" color="var(--c-warn)" /></template>
        <template #accessory><UiButton size="sm" :loading="busy === s.id" @click="run(s.id)">Start</UiButton></template>
      </UiListRow>
    </UiList>
    <template v-if="netAvailable.length">
      <h3 class="sec">Network</h3>
      <UiList>
        <UiListRow v-for="s in NET.filter((n) => netAvailable.includes(n.id))" :key="s.id" :title="s.title" :detail="`${s.what} RadarOps ${s.ai}`">
          <template #leading><UiAppTile :icon="s.icon" color="var(--c-warn)" /></template>
          <template #accessory><UiButton size="sm" :loading="busy === s.id" @click="run(s.id)">Start</UiButton></template>
        </UiListRow>
      </UiList>
    </template>
    <UiList class="mt"><UiListRow title="Reset everything" subtitle="Clears injected faults, the attack, the firewall block list and any network fault">
      <template #leading><UiAppTile icon="arrow_sync" color="var(--c-neutral)" /></template>
      <template #accessory><UiButton variant="tint" size="sm" :loading="busy === 'reset'" @click="run('reset')">Reset</UiButton></template></UiListRow></UiList>
  </div>
</template>
<style scoped>
.sec { font-size: var(--fs-sm); font-weight: 600; color: var(--c-text-2); margin: 22px 0 8px; }
.sec--first { margin-top: 0; }
.note { margin: -4px 0 10px; }
</style>
