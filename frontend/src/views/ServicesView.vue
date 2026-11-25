<script setup>
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePageFacts } from "@/composables/usePageFacts";
import { rollup } from "@/lib/insight";
import { usePolling } from "@/composables/usePolling";
import { useCatalogStore } from "@/stores/catalog";

const cat = useCatalogStore();
usePolling(() => cat.loadServices(), 10000);
usePageFacts(() => cat.loaded ? {
  applications: cat.applications.length, network_devices: cat.network.length,
  discovered_services: cat.discoveredProcesses.length, services_with_issues: rollup(cat.services).affected,
} : {});
</script>
<template>
  <div class="page">
    <UiPageHeader eyebrow="Watch" title="Services" subtitle="Everything SIT-AIOPS watches. Apps that send data are added on their own, within a minute.">
      <UiButton icon="add" to="/connect">Connect</UiButton>
    </UiPageHeader>
    <UiSkeletonPage v-if="!cat.loaded" :header="false" :rows="7" />
    <template v-else>
    <div class="section-label">Applications ({{ cat.applications.length }})</div>
    <UiList><ServiceRow v-for="s in cat.applications" :key="s.service" :service="s" /><UiEmpty v-if="cat.loaded && !cat.applications.length">None yet</UiEmpty></UiList>
    <div class="section-label">Network devices ({{ cat.network.length }})</div>
    <UiList><ServiceRow v-for="s in cat.network" :key="s.service" :service="s" /></UiList>
    <div class="section-label">Discovered on computers ({{ cat.discoveredProcesses.length }})</div>
    <UiList><ServiceRow v-for="s in cat.discoveredProcesses" :key="s.service" :service="s" />
      <UiEmpty v-if="cat.loaded && !cat.discoveredProcesses.length">Connect a computer and its services appear here automatically.</UiEmpty></UiList>
    </template>
  </div>
</template>
