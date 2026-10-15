<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const route = useRoute();
const router = useRouter();
const scanOpen = ref(false);
const authorised = ref(false);
const scanning = ref(false);
const hosts = computed(() => d.value?.summary.listening_on || []);
async function requestScan() {
  scanning.value = true;
  try {
    await Promise.all(hosts.value.map((h) => api.hosts.netscan(h)));
    ui.toast("Scan requested. Results appear within a minute.");
    scanOpen.value = false; authorised.value = false;
  } catch (e) {
    ui.toast(e.message);
  } finally {
    scanning.value = false;
  }
}
const view = ref(["network", "service", "org"].includes(route.query.view) ? route.query.view : "network");
watch(view, (v) => { router.replace({ query: v === "network" ? {} : { view: v } }); load(); });
const d = ref(null);
const error = ref("");
async function load() {
  try { d.value = await api.network.discovered(view.value); error.value = ""; } catch (e) { error.value = e.message; }
}
usePolling(load, 20000);

const VIEWS = [{ value: "network", label: "Network" }, { value: "service", label: "Service" }, { value: "org", label: "Owner" }];
const ICON = { gateway: "globe", connected: "server", "virtual machine": "cube", container: "apps", device: "hard_drive", "random MAC": "laptop" };
const KIND = { gateway: "Gateway", connected: "On AIOps", "virtual machine": "Virtual machine", container: "Container", device: "Device", "random MAC": "Random MAC" };
const sub = (i) => [i.name && i.name !== i.ip ? i.ip : null, i.vendor || (i.kind === "connected" ? null : "vendor unknown"), i.mac,
  i.services?.length ? `runs ${i.services.slice(0, 3).join(", ")}${i.services.length > 3 ? " …" : ""}` : null,
  i.talks_with?.length ? `talks with ${i.talks_with.join(", ")}` : null, i.last_seen ? `heard ${ago(i.last_seen)}` : null].filter(Boolean).join(" · ");
const empty = computed(() => d.value && !d.value.groups.length);
</script>
<template>
  <div class="page">
    <UiPageHeader title="Fleet list"
                  subtitle="Every machine across your networks, as a list. By default the agent only listens to the announcements each machine makes; use “Scan a segment” to also find the quiet ones on a network you are authorised to scan.">
      <UiButton v-if="hosts.length" variant="tint" icon="search" @click="scanOpen = true">Scan a segment</UiButton>
      <UiButton icon="flowchart" to="/network">Map</UiButton>
      <UiButton variant="tint" icon="cube" to="/network/3d">3D</UiButton>
    </UiPageHeader>
    <UiSheet v-model="scanOpen" title="Scan a segment once">
      <p class="muted">By default AIOps only listens. This asks each connected server ({{ hosts.join(", ") }}) to send one round of ARP requests across <b>its own network segment</b> to find machines that stay quiet. It never touches another network and never probes a service port.</p>
      <p class="muted mt-2">Only do this on a network you are authorised to scan. On a shared network, get the owner's permission first.</p>
      <div class="row mt"><UiSwitch v-model="authorised" label="I am authorised to scan this network" /><span>I am authorised to scan this network</span></div>
      <template #footer>
        <UiButton variant="plain" @click="scanOpen = false">Cancel</UiButton>
        <UiButton :disabled="!authorised || scanning" @click="requestScan">{{ scanning ? "Requesting…" : "Scan once" }}</UiButton>
      </template>
    </UiSheet>
    <div class="bar">
      <UiSegmented v-model="view" :options="VIEWS" label="Group by" />
      <span v-if="d" class="muted small">{{ d.summary.machines }} machines · {{ d.summary.segments }} segment{{ d.summary.segments === 1 ? "" : "s" }} · listening on {{ d.summary.listening_on.join(", ") || "-" }}</span>
    </div>
    <p v-if="error" class="bad small">{{ error }}</p>
    <UiEmpty v-if="empty">No segment yet. Connect a Linux server from Add a host: its agent starts listening within a minute.</UiEmpty>
    <section v-for="g in d?.groups || []" :key="g.title" class="group">
      <div class="ghead">
        <b>{{ g.title }}</b>
        <span v-if="g.gateway" class="muted small">gateway {{ g.gateway }} · heard by {{ g.seen_by.join(", ") }}</span>
        <span class="pills"><UiPill v-for="(n, k) in g.counts" :key="k" :mark="false">{{ n }} {{ KIND[k] || k }}</UiPill></span>
      </div>
      <UiList>
        <UiListRow v-for="i in g.items" :key="`${g.title}-${i.ip}`" :title="i.name || i.ip" :subtitle="sub(i)"
                   :to="i.aiops_host ? `/computers/${i.aiops_host}` : undefined">
          <template #leading><UiAppTile :icon="ICON[i.kind] || 'hard_drive'" :size="34" /></template>
          <template #accessory><UiPill :tone="i.kind === 'connected' ? 'ok' : i.kind === 'gateway' ? 'info' : 'neutral'">{{ KIND[i.kind] || i.kind }}</UiPill></template>
        </UiListRow>
      </UiList>
    </section>
  </div>
</template>
<style scoped>
.bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.group { margin-bottom: 22px; }
.ghead { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin: 0 2px 8px; }
.ghead b { font-size: var(--fs-lg); }
.pills { display: flex; gap: 6px; flex-wrap: wrap; margin-left: auto; }
</style>
