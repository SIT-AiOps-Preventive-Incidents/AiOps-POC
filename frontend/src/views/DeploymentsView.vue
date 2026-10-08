<script setup>
import { ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
const rows = ref([]);
usePolling(async () => { rows.value = await api.deployments.list(); }, 15000);
const color = (d) => (d.profile === "bad" ? "var(--c-bad)" : d.author.startsWith("aiops") ? "var(--c-ok)" : "var(--c-primary)");
</script>
<template>
  <div class="page">
    <UiPageHeader title="Deployments" subtitle="Versions and commits reported by CI. The AI uses them to tie a problem to the change behind it." />
    <UiList>
      <UiListRow v-for="d in rows" :key="d.id" :title="`${d.service} v${d.version} · ${d.commit_hash}`" :subtitle="`${d.author} · ${d.message}`">
        <template #leading><UiAppTile icon="branch" :color="color(d)" /></template>
        <template #accessory>{{ ago(d.ts) }}</template>
      </UiListRow>
    </UiList>
  </div>
</template>
