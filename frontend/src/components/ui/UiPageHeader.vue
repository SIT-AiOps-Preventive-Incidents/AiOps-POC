<script setup>
import UiIcon from "./UiIcon.vue";
defineProps({ title: String, subtitle: String, back: Object }); // back: { to, label }
</script>
<template>
  <header class="ui-ph">
    <div class="ui-ph__text">
      <router-link v-if="back" :to="back.to" class="ui-ph__back"><UiIcon name="chevron_left" :size="18" />{{ back.label }}</router-link>
      <h1>{{ title }}</h1>
      <p v-if="subtitle || $slots.subtitle" class="ui-ph__sub"><slot name="subtitle">{{ subtitle }}</slot></p>
    </div>
    <div v-if="$slots.default" class="ui-ph__actions"><slot /></div>
  </header>
</template>
<style scoped>
.ui-ph { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding: 18px 0; }
.ui-ph__text { min-width: 0; }
.ui-ph h1 { font-size: var(--fs-3xl); line-height: 1.15; font-weight: var(--fw-bold); letter-spacing: -0.025em; }
.ui-ph__sub { color: var(--c-text-2); margin-top: 6px; max-width: 72ch; }
.ui-ph__back { display: inline-flex; align-items: center; gap: 2px; margin-bottom: 4px; }
.ui-ph__actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
@media (max-width: 760px) { .ui-ph h1 { font-size: 28px; } }
</style>
