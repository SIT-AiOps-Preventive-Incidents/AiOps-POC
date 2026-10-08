<script setup lang="ts">
import { computed } from "vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import ProblemCard from "@/components/common/ProblemCard.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
const state = useAsyncState(api.incidents, 6000);
const approval = computed(
  () => state.data?.filter((p) => p.status === "awaiting_approval") || [],
);
const active = computed(
  () =>
    state.data?.filter((p) =>
      [
        "open",
        "analyzing",
        "remediating",
        "verifying",
        "remediation_failed",
      ].includes(p.status),
    ) || [],
);
const closed = computed(
  () =>
    state.data
      ?.filter((p) => ["resolved", "rejected", "closed"].includes(p.status))
      .slice(0, 30) || [],
);
</script>
<template>
  <div class="page">
    <PageHeader
      title="Problems"
      description="The AI investigates every problem. Fixes are dry-run first and only applied after the owner approves."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><template v-else
      ><section>
        <h2>Needs your approval ({{ approval.length }})</h2>
        <div v-if="approval.length" class="cards">
          <ProblemCard v-for="p in approval" :key="p.id" :problem="p" />
        </div>
        <EmptyState v-else title="Nothing is waiting for approval" />
      </section>
      <section>
        <h2>In progress ({{ active.length }})</h2>
        <div v-if="active.length" class="cards">
          <ProblemCard v-for="p in active" :key="p.id" :problem="p" />
        </div>
        <EmptyState v-else title="No problems are being worked on" />
      </section>
      <section>
        <h2>Recently closed</h2>
        <div v-if="closed.length" class="cards">
          <ProblemCard v-for="p in closed" :key="p.id" :problem="p" />
        </div>
        <EmptyState
          v-else
          title="No history yet"
          message="Try a demo scenario to exercise the incident workflow."
        /></section
    ></template>
  </div>
</template>
<style scoped>
section {
  margin-bottom: 22px;
}
section h2 {
  font-size: 15px;
}
.cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
@media (max-width: 900px) {
  .cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .cards {
    grid-template-columns: 1fr;
  }
}
</style>
