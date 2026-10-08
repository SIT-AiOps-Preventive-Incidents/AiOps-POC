<script setup>
import { usePolling } from "@/composables/usePolling";
import { HEALTH_TONE, osLogo } from "@/lib/vocab";
import { useCatalogStore } from "@/stores/catalog";
const cat = useCatalogStore();
usePolling(() => cat.loadHosts(), 10000);
</script>
<template>
  <div class="page">
    <UiPageHeader title="Computers & Servers" subtitle="Machines that report CPU, memory and disk - and the services found running on them.">
      <UiButton icon="add" to="/connect/computer">Connect a computer</UiButton>
    </UiPageHeader>
    <div class="grid grid--3">
      <router-link v-for="h in cat.hosts" :key="h.name" :to="`/computers/${h.name}`" class="card">
        <div class="row"><UiAppTile :logo="osLogo(h.os)" :icon="h.kind === 'workstation' ? 'laptop' : 'server'" :status="HEALTH_TONE[h.status]" :size="36" />
          <div class="grow"><b>{{ h.name }}</b><div class="small muted ell">{{ h.os }}</div></div>
          <UiPill v-if="h.problem_id" tone="bad">Problem</UiPill>
          <UiPill v-else :tone="h.status === 'healthy' ? 'ok' : 'neutral'">{{ h.status === "healthy" ? "Online" : h.status === "offline" ? "Offline" : "Waiting" }}</UiPill></div>
        <div class="mt-2"><UiMeter label="CPU" :value="h.cpu" /><UiMeter label="Memory" :value="h.mem" :warn="80" /><UiMeter label="Disk" :value="h.disk" :warn="80" /></div>
        <div class="small dim mt-2">{{ h.services.length }} services · {{ h.agent === "aiops-agent" ? "AIOps agent" : "node_exporter" }}</div>
      </router-link>
      <router-link to="/connect/computer" class="card add"><UiIcon name="add_circle" :size="30" /><b>Connect a computer</b></router-link>
    </div>
  </div>
</template>
<style scoped>
.card { display: block; background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 18px 20px; color: var(--c-text); }
.card:hover { box-shadow: 0 0 0 1.5px var(--c-primary); }
.grow { flex: 1; min-width: 0; } .ell { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.add { display: grid; place-items: center; align-content: center; gap: 6px; color: var(--c-primary); min-height: 190px; border: 2px dashed var(--c-primary-tint-2); box-shadow: none; background: transparent; }
</style>
