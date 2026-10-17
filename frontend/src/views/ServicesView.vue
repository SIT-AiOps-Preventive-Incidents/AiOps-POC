<script setup>
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { useCatalogStore } from "@/stores/catalog";

const cat = useCatalogStore();
usePolling(() => cat.loadServices(), 10000);
</script>
<template>
  <div class="page">
    <UiPageHeader title="Services" subtitle="Everything RadarOps watches. Apps that send data are added on their own, within a minute.">
      <UiButton icon="add" to="/connect">Connect</UiButton>
    </UiPageHeader>
    <div class="section-label">Applications ({{ cat.applications.length }})</div>
    <UiList><ServiceRow v-for="s in cat.applications" :key="s.service" :service="s" /><UiEmpty v-if="cat.loaded && !cat.applications.length">None yet</UiEmpty></UiList>
    <div class="section-label">Network devices ({{ cat.network.length }})</div>
    <UiList><ServiceRow v-for="s in cat.network" :key="s.service" :service="s" /></UiList>
    <div class="section-label">Discovered on computers ({{ cat.discoveredProcesses.length }})</div>
    <UiList><ServiceRow v-for="s in cat.discoveredProcesses" :key="s.service" :service="s" />
      <UiEmpty v-if="cat.loaded && !cat.discoveredProcesses.length">Connect a computer and its services appear here automatically.</UiEmpty></UiList>
  </div>
</template>
