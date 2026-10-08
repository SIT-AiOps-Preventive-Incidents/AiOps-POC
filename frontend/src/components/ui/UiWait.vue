<script setup>
// Live waiting / success box used by the connect flows and by "AI is investigating".
import UiIcon from "./UiIcon.vue";
import UiSpinner from "./UiSpinner.vue";
defineProps({ done: Boolean, title: String, subtitle: String });
</script>
<template>
  <div :class="['ui-wait', { done }]" role="status">
    <UiIcon v-if="done" name="checkmark_circle" filled :size="24" />
    <UiSpinner v-else />
    <div><b>{{ title }}</b><div class="small"><slot>{{ subtitle }}</slot></div></div>
  </div>
</template>
<style scoped>
.ui-wait { display: flex; align-items: center; gap: 12px; padding: 14px 16px; border-radius: 12px; background: var(--c-fill); }
.ui-wait.done { background: var(--c-ok-bg); color: var(--c-ok-text); }
</style>
