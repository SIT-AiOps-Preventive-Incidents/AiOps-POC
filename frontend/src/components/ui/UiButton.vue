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
    <UiSpinner v-if="loading" :size="size === 'sm' ? 15 : 17" />
    <UiIcon v-else-if="icon" :name="icon" :size="size === 'sm' ? 16 : size === 'lg' ? 19 : 17" class="ui-btn__ic" />
    <slot />
  </component>
</template>
<style scoped>
/* Buttons: filled actions carry a soft one-pixel shadow and a top inner highlight for depth, lighten on hover,
   and push in on press - the restrained, tactile style of a modern product (Linear / Vercel / Stripe). */
.ui-btn { display: inline-flex; align-items: center; justify-content: center; gap: 7px; border: 1px solid transparent; cursor: pointer;
  font-weight: var(--fw-semibold); white-space: nowrap; border-radius: var(--radius-md); text-decoration: none; line-height: 1;
  letter-spacing: 0.01em; -webkit-user-select: none; user-select: none; -webkit-tap-highlight-color: transparent;
  transition: background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease), filter var(--dur-fast) var(--ease); }
.ui-btn__ic { flex: none; }
.ui-btn:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.ui-btn:active:not(:disabled) { transform: translateY(0.5px); }
.ui-btn--sm { height: 30px; padding: 0 11px; font-size: var(--fs-sm); border-radius: var(--radius-sm); }
.ui-btn--md { height: 36px; padding: 0 15px; font-size: var(--fs-md); }
.ui-btn--lg { height: 44px; padding: 0 20px; font-size: var(--fs-lg); border-radius: var(--radius-lg); }
.ui-btn--block { width: 100%; }

/* filled — primary (blue = the system) */
.ui-btn--primary { background: linear-gradient(var(--c-primary), var(--c-primary-hover)); color: var(--c-on-primary);
  box-shadow: 0 1px 2px rgba(15, 18, 24, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.14); }
.ui-btn--primary:hover:not(:disabled) { background: linear-gradient(var(--c-primary-hover), var(--c-primary-press)); }
.ui-btn--primary:active:not(:disabled) { background: var(--c-primary-press); box-shadow: 0 1px 1px rgba(15, 18, 24, 0.22); }

/* filled — action (orange = your turn) */
.ui-btn--action { background: linear-gradient(var(--c-action), var(--c-action-hover)); color: var(--c-on-action);
  box-shadow: 0 1px 2px rgba(15, 18, 24, 0.18), inset 0 1px 0 rgba(255, 255, 255, 0.18); }
.ui-btn--action:hover:not(:disabled) { filter: brightness(1.04); }
.ui-btn--action:active:not(:disabled) { background: var(--c-action-hover); filter: none; box-shadow: 0 1px 1px rgba(15, 18, 24, 0.22); }

/* secondary — tint (surface + hairline border) */
.ui-btn--tint { background: var(--c-surface); color: var(--c-text); border-color: var(--c-border); box-shadow: 0 1px 1.5px rgba(15, 18, 24, 0.05); }
.ui-btn--tint:hover:not(:disabled) { background: var(--c-fill); border-color: var(--c-text-3); }
.ui-btn--tint:active:not(:disabled) { background: var(--c-fill-2); }

/* ghost — transparent, for toolbars and icon-only buttons */
.ui-btn--ghost { background: transparent; color: var(--c-text-2); }
.ui-btn--ghost:hover:not(:disabled) { background: var(--c-fill); color: var(--c-text); }

/* plain — text button */
.ui-btn--plain { background: none; color: var(--c-primary); padding: 0 7px; }
.ui-btn--plain:hover:not(:disabled) { background: var(--c-primary-tint); }

/* danger — destructive */
.ui-btn--danger { background: none; color: var(--c-bad-text); border-color: var(--c-border); }
.ui-btn--danger:hover:not(:disabled) { background: var(--c-bad-bg); border-color: var(--c-bad); }

.ui-btn:disabled { background: var(--c-fill); color: var(--c-text-3); border-color: transparent; cursor: default; box-shadow: none; transform: none; filter: none; }
.ui-btn--plain:disabled, .ui-btn--ghost:disabled { background: none; }
@media (prefers-reduced-motion: reduce) { .ui-btn:active:not(:disabled) { transform: none; } }
</style>
