<script setup lang="ts">
withDefaults(defineProps<{ tone?: "success" | "danger" | "neutral" }>(), {
  tone: "success",
});
</script>
<template>
  <span class="status-chip" :class="`status-chip--${tone}`"><slot /></span>
</template>
<style scoped>
.status-chip {
  display: inline-flex;
  height: 28px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border-default);
  border-radius: 999px;
  background: white;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 500;
  line-height: 16px;
  white-space: nowrap;
}
.status-chip--success {
  color: var(--color-status-success-text);
}
.status-chip--danger {
  color: var(--color-status-danger-text);
}
.status-chip--neutral {
  color: var(--color-text-muted);
}
</style>
