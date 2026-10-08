<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: "primary" | "secondary" | "danger" | "ghost";
    disabled?: boolean;
    type?: "button" | "submit";
  }>(),
  { variant: "primary", disabled: false, type: "button" },
);
</script>

<template>
  <button
    :type="type"
    class="button"
    :class="`button--${variant}`"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped>
.button {
  display: inline-flex;
  height: 36px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  cursor: pointer;
  white-space: nowrap;
  transition:
    background 0.15s,
    border-color 0.15s;
}
.button--primary {
  background: var(--color-accent-primary);
  color: white;
}
.button--primary:hover {
  background: var(--color-accent-primary-hover);
}
.button--secondary {
  background: white;
  border-color: var(--color-border-strong);
  color: var(--color-text-default);
}
.button--secondary:hover,
.button--ghost:hover {
  background: var(--color-status-info-bg);
}
.button--danger {
  background: var(--color-status-danger);
  color: white;
}
.button--ghost {
  background: transparent;
  color: var(--color-accent-primary);
}
.button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
