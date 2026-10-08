<script setup lang="ts">
import { RouterLink } from "vue-router";
import BaseBadge from "./BaseBadge.vue";
import { ago, titleCase } from "@/utils/format";
import type { Incident } from "@/types/api";
const props = defineProps<{ problem: Incident }>();
const tone = (): "ai" | "success" | "danger" | "warning" =>
  props.problem.status === "awaiting_approval"
    ? "ai"
    : props.problem.status === "resolved"
      ? "success"
      : props.problem.status === "remediation_failed"
        ? "danger"
        : "warning";
</script>
<template>
  <RouterLink class="problem" :to="`/problems/${problem.id}`"
    ><strong>P-{{ problem.id }}</strong
    ><span>{{ problem.title }}</span
    ><small
      >{{ problem.entity_type }}: {{ problem.entity }} ·
      {{ ago(problem.detected_at) }}</small
    ><BaseBadge :tone="tone()">{{
      titleCase(problem.status)
    }}</BaseBadge></RouterLink
  >
</template>
<style scoped>
.problem {
  display: flex;
  min-height: 128px;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: white;
  padding: 14px;
}
.problem span,
.problem strong {
  font-weight: 600;
}
.problem small {
  color: var(--color-text-dim);
  font-size: 12px;
}
.problem:hover {
  border-color: var(--color-accent-primary);
}
</style>
