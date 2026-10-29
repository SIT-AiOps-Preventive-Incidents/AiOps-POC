<script setup>
import UiIcon from "./UiIcon.vue";
// eyebrow: a quiet line above the title that says where you are (e.g. the environment or the parent page)
defineProps({ title: String, subtitle: String, eyebrow: String, back: Object }); // back: { to, label }
</script>
<template>
  <header class="ui-ph">
    <div class="ui-ph__text">
      <router-link v-if="back" :to="back.to" class="ui-ph__back"><UiIcon name="chevron_left" :size="16" />{{ back.label }}</router-link>
      <p v-else-if="eyebrow" class="ui-ph__eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="subtitle || $slots.subtitle" class="ui-ph__sub"><slot name="subtitle">{{ subtitle }}</slot></p>
    </div>
    <div v-if="$slots.default" class="ui-ph__actions"><slot /></div>
  </header>
</template>
<style scoped>
.ui-ph { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; padding: 8px 0 22px; }
.ui-ph__text { min-width: 0; }
.ui-ph__eyebrow { font-size: var(--fs-md); color: var(--c-text-3); margin-bottom: 2px; }
.ui-ph h1 { font-size: var(--fs-3xl); line-height: var(--lh-tight); font-weight: var(--fw-bold); letter-spacing: -0.03em; }
.ui-ph__sub { color: var(--c-text-2); margin-top: 8px; max-width: 78ch; }
.ui-ph__back { display: inline-flex; align-items: center; gap: 2px; margin-bottom: 4px; font-size: var(--fs-md); color: var(--c-text-3); }
.ui-ph__back:hover { color: var(--c-text); }
.ui-ph__actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
@media (max-width: 760px) { .ui-ph h1 { font-size: 26px; } }
</style>
