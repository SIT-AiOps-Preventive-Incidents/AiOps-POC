<script setup lang="ts">
import BaseBadge from "@/components/common/BaseBadge.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { percent } from "@/utils/format";
const state = useAsyncState(api.skills);
</script>
<template>
  <div class="page">
    <PageHeader
      title="Skills & Scores"
      description="The AI picks one read-only skill per problem. Your ratings tune future investigations."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    />
    <div v-else-if="state.data?.length" class="skills">
      <BasePanel v-for="skill in state.data" :key="skill.id"
        ><template #header
          ><h2>{{ skill.name }}</h2>
          <BaseBadge tone="info">{{ skill.category }}</BaseBadge></template
        >
        <p class="muted">{{ skill.description }}</p>
        <div class="metrics">
          <span
            ><small>Used</small><b>{{ skill.runs }}</b></span
          ><span
            ><small>Rating</small><b>{{ skill.avg_score ?? "—" }}</b></span
          ><span
            ><small>Correct</small
            ><b>{{
              skill.accuracy == null ? "—" : percent(skill.accuracy, 0)
            }}</b></span
          ><span
            ><small>Takes</small
            ><b>{{ skill.avg_analysis_s ?? "—" }} s</b></span
          >
        </div>
        <details>
          <summary>Tools ({{ skill.tools.length }})</summary>
          <code>{{ skill.tools.join(" · ") }}</code>
        </details>
        <div v-if="skill.lessons.length" class="lessons">
          <b>Learning from feedback</b>
          <p v-for="lesson in skill.lessons" :key="lesson">· {{ lesson }}</p>
        </div></BasePanel
      >
    </div>
    <EmptyState v-else title="No skills available" />
  </div>
</template>
<style scoped>
.skills {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 14px 0;
}
.metrics span {
  display: flex;
  flex-direction: column;
}
.metrics small {
  color: var(--color-text-muted);
}
details code {
  display: block;
  margin-top: 6px;
  color: var(--color-text-muted);
}
.lessons {
  margin-top: 12px;
}
.lessons p {
  margin: 3px 0;
  color: var(--color-text-muted);
  font-size: 12px;
}
@media (max-width: 760px) {
  .skills {
    grid-template-columns: 1fr;
  }
}
</style>
