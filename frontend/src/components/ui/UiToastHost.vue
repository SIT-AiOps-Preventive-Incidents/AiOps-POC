<script setup>
import { useUiStore } from "@/stores/ui";
const ui = useUiStore();
</script>
<template>
  <div class="toasts" role="status" aria-live="polite">
    <TransitionGroup name="toast"><div v-for="t in ui.toasts" :key="t.id" class="toast">{{ t.message }}</div></TransitionGroup>
  </div>
</template>
<style scoped>
.toasts { position: fixed; left: 50%; bottom: calc(24px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); z-index: 60; display: flex; flex-direction: column; gap: 8px; align-items: center; }
.toast { background: var(--c-toast); color: #fff; padding: 10px 18px; border-radius: var(--radius-pill); font-size: 14px; font-weight: var(--fw-medium); box-shadow: var(--shadow-2); }
.toast-enter-active, .toast-leave-active { transition: opacity var(--dur) var(--ease), transform var(--dur) var(--ease); }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateY(8px); }
</style>
