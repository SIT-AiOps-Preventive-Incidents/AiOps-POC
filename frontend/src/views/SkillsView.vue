<script setup>
import { ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
const skills = ref([]);
usePolling(async () => { skills.value = await api.skills.list(); }, 30000);
</script>
<template>
  <div class="page">
    <UiPageHeader title="Skills & Scores" subtitle="The AI picks one skill per problem. Skills can only read data; your ratings tune them." />
    <div class="grid grid--2">
      <UiCard v-for="s in skills" :key="s.id">
        <div class="row row--between"><h2 class="t">{{ s.name }}</h2><UiPill tone="info">{{ s.category }}</UiPill></div>
        <p class="small muted">{{ s.description }}</p>
        <div class="grid grid--4 mt-2 stats">
          <div><span>Used</span><b>{{ s.runs }}</b></div><div><span>Rating</span><b>{{ s.avg_score ?? "-" }}</b></div>
          <div><span>Correct</span><b>{{ s.accuracy == null ? "-" : `${Math.round(s.accuracy * 100)}%` }}</b></div><div><span>Takes</span><b>{{ s.avg_analysis_s ?? "-" }} s</b></div>
        </div>
        <UiDisclosure :card="false" :title="`Tools (${s.tools?.length || 0})`" class="mt-2"><p class="small mono muted">{{ (s.tools || []).join(" · ") }}</p></UiDisclosure>
        <div v-if="s.lessons.length" class="small mt-2"><b>Learning from feedback</b><div v-for="l in s.lessons" :key="l" class="muted">· {{ l }}</div></div>
      </UiCard>
    </div>
  </div>
</template>
<style scoped>
.t { font-size: var(--fs-lg); } .stats span { display: block; font-size: var(--fs-sm); color: var(--c-text-2); }
</style>
