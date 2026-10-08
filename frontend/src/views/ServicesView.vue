<script setup>
import { ref } from "vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const cat = useCatalogStore();
const ui = useUiStore();
usePolling(() => cat.loadServices(), 10000);
const adding = ref(null);
const owner = ref(ui.prefs.lastOwner || "");
async function add() {
  try {
    await cat.addService({ service_name: adding.value, owner: owner.value || "unassigned" });
    ui.setPref("lastOwner", owner.value);
    ui.toast(`${adding.value} added`);
    adding.value = null;
  } catch (e) { ui.toast(e.message); }
}
</script>
<template>
  <div class="page">
    <UiPageHeader title="Services" subtitle="Applications and network devices AIOps watches, plus processes agents found on your computers.">
      <UiButton icon="add" to="/connect">Connect</UiButton>
    </UiPageHeader>
    <template v-if="cat.unregistered.length">
      <div class="section-label">Sending data, not added yet</div>
      <UiList><UiListRow v-for="s in cat.unregistered" :key="s.service_name" :title="s.service_name" :subtitle="s.rps ? `${s.rps} req/s` : 'Sending logs'">
        <template #leading><UiAppTile icon="sparkle" color="var(--c-primary)" /></template>
        <template #accessory><UiButton size="sm" @click="adding = s.service_name">Add</UiButton></template></UiListRow></UiList>
    </template>
    <div class="section-label">Applications ({{ cat.applications.length }})</div>
    <UiList><ServiceRow v-for="s in cat.applications" :key="s.service" :service="s" /><UiEmpty v-if="cat.loaded && !cat.applications.length">None yet</UiEmpty></UiList>
    <div class="section-label">Network devices ({{ cat.network.length }})</div>
    <UiList><ServiceRow v-for="s in cat.network" :key="s.service" :service="s" /></UiList>
    <div class="section-label">Discovered on computers ({{ cat.discoveredProcesses.length }})</div>
    <UiList><ServiceRow v-for="s in cat.discoveredProcesses" :key="s.service" :service="s" />
      <UiEmpty v-if="cat.loaded && !cat.discoveredProcesses.length">Connect a computer and its services appear here automatically.</UiEmpty></UiList>
    <UiSheet :model-value="!!adding" :title="`Add ${adding}`" @update:model-value="adding = null">
      <p class="muted">Who owns this service? The owner approves fixes for it.</p>
      <UiField v-model="owner" label="Owner team" placeholder="team-orders" @enter="add" />
      <template #footer><UiButton variant="plain" @click="adding = null">Cancel</UiButton><UiButton @click="add">Add service</UiButton></template>
    </UiSheet>
  </div>
</template>
