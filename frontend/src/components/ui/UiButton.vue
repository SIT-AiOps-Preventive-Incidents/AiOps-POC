<script setup>
import { computed } from "vue";
import UiIcon from "./UiIcon.vue";
import UiSpinner from "./UiSpinner.vue";

const props = defineProps({
  variant: { type: String, default: "primary" }, // primary | action (orange: your turn) | tint | plain | danger | ghost
  size: { type: String, default: "md" },        // sm | md | lg
  to: [String, Object], href: String, icon: String, block: Boolean, loading: Boolean, disabled: Boolean,
  type: { type: String, default: "button" },
});
const tag = computed(() => (props.to ? "router-link" : props.href ? "a" : "button"));
</script>
<template>
  <component :is="tag" :to="to" :href="href" :type="tag === 'button' ? type : undefined"
             :class="['ui-btn', `ui-btn--${variant}`, `ui-btn--${size}`, { 'ui-btn--block': block }]"
             :disabled="tag === 'button' ? disabled || loading : undefined" :aria-busy="loading || undefined"
             :target="href ? '_blank' : undefined" :rel="href ? 'noopener' : undefined">
    <UiSpinner v-if="loading" :size="16" />
    <UiIcon v-else-if="icon" :name="icon" :size="size === 'sm' ? 16 : 18" />
    <slot />
  </component>
</template>
<style scoped>
.ui-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid transparent; cursor: pointer;
  font-weight: var(--fw-medium); white-space: nowrap; border-radius: var(--radius-md); text-decoration: none; line-height: 1;
  transition: background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
.ui-btn--sm { height: 28px; padding: 0 10px; font-size: var(--fs-sm); }
.ui-btn--md { height: 34px; padding: 0 14px; font-size: var(--fs-md); }
.ui-btn--lg { height: 42px; padding: 0 18px; font-size: var(--fs-lg); }
.ui-btn--block { width: 100%; }
.ui-btn--primary { background: var(--c-primary); color: var(--c-on-primary); }
.ui-btn--primary:hover:not(:disabled) { background: var(--c-primary-hover); }
.ui-btn--action { background: var(--c-action); color: var(--c-on-action); }
.ui-btn--action:hover:not(:disabled) { background: var(--c-action-hover); }
.ui-btn--tint, .ui-btn--ghost { background: var(--c-surface); color: var(--c-text); border-color: var(--c-border); }
.ui-btn--tint:hover:not(:disabled), .ui-btn--ghost:hover:not(:disabled) { background: var(--c-fill); }
.ui-btn--plain { background: none; color: var(--c-primary); padding: 0 6px; }
.ui-btn--plain:hover:not(:disabled) { background: var(--c-primary-tint); }
.ui-btn--danger { background: none; color: var(--c-bad-text); border-color: var(--c-border); }
.ui-btn--danger:hover:not(:disabled) { background: var(--c-bad-bg); }
.ui-btn:disabled { background: var(--c-fill); color: var(--c-text-3); border-color: transparent; cursor: default; }
.ui-btn--plain:disabled { background: none; }
</style>
