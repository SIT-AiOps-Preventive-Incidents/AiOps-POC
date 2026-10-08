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
.ui-card { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 18px 20px; min-width: 0; }
.ui-card--flush { padding: 0; overflow: hidden; }
.ui-card__head { display: flex; justify-content: space-between; align-items: center; gap: var(--sp-2); margin-bottom: 10px; }
.ui-card--flush .ui-card__head { padding: 16px 20px 0; }
.ui-card__title { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); text-transform: uppercase; letter-spacing: 0.03em; }
</style>
