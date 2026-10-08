<script setup>
import { computed } from "vue";
import UiIcon from "./UiIcon.vue";
import UiSpinner from "./UiSpinner.vue";

const props = defineProps({
  variant: { type: String, default: "primary" }, // primary | tint | plain | danger | ghost
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
.ui-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 0; cursor: pointer;
  font-weight: var(--fw-semibold); white-space: nowrap; border-radius: var(--radius-md); text-decoration: none;
  transition: background var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease); }
.ui-btn:active:not(:disabled) { transform: scale(0.98); }
.ui-btn--sm { height: 30px; padding: 0 12px; font-size: var(--fs-sm); border-radius: var(--radius-sm); }
.ui-btn--md { height: 36px; padding: 0 16px; font-size: var(--fs-md); }
.ui-btn--lg { height: 50px; padding: 0 20px; font-size: var(--fs-lg); border-radius: 12px; }
.ui-btn--block { width: 100%; }
.ui-btn--primary { background: var(--c-primary); color: var(--c-on-primary); }
.ui-btn--primary:hover:not(:disabled) { background: var(--c-primary-hover); }
.ui-btn--tint { background: var(--c-primary-tint); color: var(--c-primary); }
.ui-btn--tint:hover:not(:disabled) { background: var(--c-primary-tint-2); }
.ui-btn--plain { background: none; color: var(--c-primary); padding: 0 8px; }
.ui-btn--plain:hover:not(:disabled) { background: var(--c-primary-tint); }
.ui-btn--danger { background: none; color: var(--c-bad-text); }
.ui-btn--danger:hover:not(:disabled) { background: var(--c-bad-bg); }
.ui-btn--ghost { background: var(--c-surface); color: var(--c-text); box-shadow: var(--shadow-1); }
.ui-btn:disabled { background: var(--c-fill-2); color: var(--c-text-3); cursor: default; }
.ui-btn--plain:disabled, .ui-btn--danger:disabled { background: none; }
</style>
