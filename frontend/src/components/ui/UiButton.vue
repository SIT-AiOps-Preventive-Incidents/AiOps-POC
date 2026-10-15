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
    <UiSpinner v-if="loading" :size="size === 'sm' ? 14 : 15" />
    <UiIcon v-else-if="icon" :name="icon" :size="size === 'sm' ? 15 : size === 'lg' ? 17 : 16" class="ui-btn__ic" />
    <slot />
  </component>
</template>
<style scoped>
/* Buttons: flat, restrained, enterprise. Solid fills for the two signal colours, a hairline outline for the
   neutral/secondary button; a faint shadow for depth, a crisp focus ring, a small push on press. No gradients. */
.ui-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid transparent; cursor: pointer;
  font-weight: var(--fw-medium); white-space: nowrap; border-radius: var(--radius-md); text-decoration: none; line-height: 1;
  -webkit-user-select: none; user-select: none; -webkit-tap-highlight-color: transparent;
  transition: background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease); }
.ui-btn__ic { flex: none; }
.ui-btn:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.ui-btn:active:not(:disabled) { transform: translateY(0.5px); }
.ui-btn--sm { height: 28px; padding: 0 10px; font-size: var(--fs-sm); border-radius: var(--radius-sm); }
.ui-btn--md { height: 32px; padding: 0 13px; font-size: var(--fs-sm); }
.ui-btn--lg { height: 38px; padding: 0 16px; font-size: var(--fs-md); }
.ui-btn--block { width: 100%; }

/* filled — primary (blue = the system) */
.ui-btn--primary { background: var(--c-primary); color: var(--c-on-primary); box-shadow: 0 1px 1px rgba(15, 18, 24, 0.08); }
.ui-btn--primary:hover:not(:disabled) { background: var(--c-primary-hover); }
.ui-btn--primary:active:not(:disabled) { background: var(--c-primary-press); }

/* filled — action (orange = your turn) */
.ui-btn--action { background: var(--c-action); color: var(--c-on-action); box-shadow: 0 1px 1px rgba(15, 18, 24, 0.08); }
.ui-btn--action:hover:not(:disabled) { background: var(--c-action-hover); }
.ui-btn--action:active:not(:disabled) { background: var(--c-action-hover); }

/* secondary — neutral outline */
.ui-btn--tint { background: var(--c-surface); color: var(--c-text); border-color: var(--c-border); }
.ui-btn--tint:hover:not(:disabled) { background: var(--c-fill); border-color: var(--c-text-3); }
.ui-btn--tint:active:not(:disabled) { background: var(--c-fill-2); }

/* ghost — transparent, for toolbars and icon-only buttons */
.ui-btn--ghost { background: transparent; color: var(--c-text-2); }
.ui-btn--ghost:hover:not(:disabled) { background: var(--c-fill); color: var(--c-text); }

/* plain — text button */
.ui-btn--plain { background: none; color: var(--c-primary); padding: 0 6px; }
.ui-btn--plain:hover:not(:disabled) { background: var(--c-primary-tint); }

/* danger — destructive */
.ui-btn--danger { background: none; color: var(--c-bad-text); border-color: var(--c-border); }
.ui-btn--danger:hover:not(:disabled) { background: var(--c-bad-bg); border-color: var(--c-bad); }

.ui-btn:disabled { background: var(--c-fill); color: var(--c-text-3); border-color: transparent; cursor: default; box-shadow: none; transform: none; }
.ui-btn--plain:disabled, .ui-btn--ghost:disabled { background: none; }
@media (prefers-reduced-motion: reduce) { .ui-btn:active:not(:disabled) { transform: none; } }
</style>
