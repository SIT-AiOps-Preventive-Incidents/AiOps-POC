<script setup>
import UiIcon from "./UiIcon.vue";
defineProps({ title: String, flush: Boolean, icon: String });
</script>
<template>
  <section :class="['ui-card', { 'ui-card--flush': flush }]">
    <header v-if="title || $slots.actions" class="ui-card__head">
      <h3 v-if="title" class="ui-card__title"><UiIcon v-if="icon" :name="icon" :size="15" class="ui-card__ic" />{{ title }}</h3>
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
.ui-card__title { display: flex; align-items: center; gap: 7px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); }
.ui-card__ic { color: var(--c-text-3); flex: none; }
</style>
