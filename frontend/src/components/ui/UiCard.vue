<script setup>
defineProps({ title: String, flush: Boolean });
</script>
<template>
  <section :class="['ui-card', { 'ui-card--flush': flush }]">
    <header v-if="title || $slots.actions" class="ui-card__head">
      <h3 v-if="title" class="ui-card__title">{{ title }}</h3>
      <slot name="actions" />
    </header>
    <slot />
  </section>
</template>
<style scoped>
.ui-card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 16px 18px; min-width: 0; }
.ui-card--flush { padding: 0; overflow: hidden; }
.ui-card__head { display: flex; justify-content: space-between; align-items: center; gap: var(--sp-2); margin-bottom: 10px; }
.ui-card--flush .ui-card__head { padding: 14px 18px 0; }
.ui-card__title { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); }
</style>
