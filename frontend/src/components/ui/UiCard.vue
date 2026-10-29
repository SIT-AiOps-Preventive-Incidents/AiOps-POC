<script setup>
// The one panel shape: a title, an optional one-line subtitle and status, the content, and - when `to` is set -
// a chevron rail on the right edge that opens the detail page.
import UiIcon from "./UiIcon.vue";
import UiStatusDot from "./UiStatusDot.vue";
defineProps({ title: String, subtitle: String, icon: String, flush: Boolean, to: [String, Object],
  status: Object, // { tone: "ok" | "bad" | "warn" | "neutral" | "info", label }
  size: { type: String, default: "md" } }); // md | lg (hero title)
</script>
<template>
  <section :class="['ui-card', `ui-card--${size}`, { 'ui-card--flush': flush, 'ui-card--link': to }]">
    <header v-if="title || $slots.actions || status" class="ui-card__head">
      <div class="ui-card__titles">
        <h3 v-if="title" class="ui-card__title"><UiIcon v-if="icon" :name="icon" :size="18" class="ui-card__ic" />{{ title }}</h3>
        <p v-if="subtitle" class="ui-card__sub">{{ subtitle }}</p>
        <p v-if="status" class="ui-card__status"><UiStatusDot :tone="status.tone" :size="9" />{{ status.label }}</p>
      </div>
      <slot name="actions" />
    </header>
    <slot />
    <router-link v-if="to" :to="to" class="ui-card__rail" :aria-label="`Open ${title || ''}`"><UiIcon name="chevron_right" :size="18" /></router-link>
  </section>
</template>
<style scoped>
.ui-card { position: relative; background: var(--surface); border-radius: 20px; box-shadow: var(--shadow-card);
  padding: 22px 24px; min-width: 0; }
.ui-card--link { padding-right: 60px; }
.ui-card--flush { padding: 0; overflow: hidden; }
.ui-card__head { display: flex; justify-content: space-between; align-items: flex-start; gap: var(--sp-3); margin-bottom: 16px; }
.ui-card--flush .ui-card__head { padding: 20px 22px 0; }
.ui-card__titles { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ui-card__title { display: flex; align-items: center; gap: 9px; font-size: var(--fs-lg); font-weight: var(--fw-semibold);
  color: var(--c-text); letter-spacing: -0.01em; line-height: var(--lh-snug); }
.ui-card--lg .ui-card__title { font-size: 22px; letter-spacing: -0.02em; }
.ui-card__ic { color: var(--c-text-3); flex: none; }
.ui-card__sub { font-size: var(--fs-sm); color: var(--c-text-3); }
.ui-card__status { display: flex; align-items: center; gap: 8px; margin-top: 8px; font-weight: var(--fw-semibold); font-size: var(--fs-md); }
/* the chevron rail: a quiet strip on the right edge, like a drawer handle */
.ui-card__rail { position: absolute; top: 0; right: 0; bottom: 0; width: 44px; display: grid; place-items: center;
  color: var(--c-text-3); border-left: 1px solid var(--c-separator); border-radius: 0 var(--radius-lg) var(--radius-lg) 0;
  transition: background var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
.ui-card__rail:hover { background: var(--c-hover); color: var(--c-text); }
@media (max-width: 560px) { .ui-card { padding: 18px; } .ui-card--link { padding-right: 54px; } }
</style>
