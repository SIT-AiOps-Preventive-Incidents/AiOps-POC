<script setup>
// Insights - what the incident history means for the business: cost, time saved, where the toil comes from, what is
// waiting, what is unseen. Every number shows how it was worked out; the two assumptions are editable in Settings.
import { ref } from "vue";
import { usePageFacts } from "@/composables/usePageFacts";
import InsightCard from "@/components/domain/InsightCard.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
const d = ref(null);
const error = ref("");
usePolling(async () => { try { d.value = await api.insights(); error.value = ""; } catch (e) { error.value = e.message; } }, 30000);
const money = (v, cur) => `${{ THB: "฿", USD: "$", EUR: "€" }[cur] || ""}${Number(v || 0).toLocaleString()}`;
usePageFacts(() => ({ findings: d.value?.findings?.length, ...(error.value && d.value ? { stale_data: 1 } : {}) }));
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Watch" title="Insights" subtitle="What your incident history means for the business: what it costs, what the AI saves, where the trouble comes from and what is waiting on people." />
    <UiSkeletonPage v-if="!d && !error" variant="dashboard" :header="false" />
    <p v-if="error" class="bad">{{ error }}</p>
    <template v-if="d">
      <div class="grid"><InsightCard v-for="f in d.findings" :key="f.id" :f="f" /></div>
      <p class="assume">Assumptions: an hour of disruption costs <b>{{ money(d.assumptions.downtime_cost_per_hour, d.assumptions.currency) }}</b>,
        a root cause found by hand takes <b>{{ d.assumptions.manual_rca_minutes }} min</b>. <router-link to="/settings">Change them in Settings</router-link>.</p>
    </template>
  </div>
</template>
<style scoped>
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 460px), 1fr)); gap: 16px; }
.assume { margin-top: 20px; font-size: var(--fs-sm); color: var(--c-text-3); }
</style>
