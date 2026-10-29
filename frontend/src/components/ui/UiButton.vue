<script setup>
import { computed } from "vue";
import UiIcon from "./UiIcon.vue";
import UiSpinner from "./UiSpinner.vue";

const props = defineProps({
  variant: { type: String, default: "primary" }, // primary | action (orange: your turn) | tint | plain | danger | ghost
  size: { type: String, default: "md" },        // sm | md | lg
  to: [String, Object], href: String, icon: String, block: Boolean, loading: Boolean, disabled: Boolean,
  chevron: Boolean, // a trailing ›: "this takes you somewhere"
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
    <UiIcon v-if="chevron" name="chevron_right" :size="size === 'sm' ? 14 : 16" class="ui-btn__chev" />
  </component>
</template>
<style scoped>
/* Buttons: soft rounded rectangles. One solid accent for the main action; quiet filled neutrals for the rest.
   A crisp focus ring and a small push on press. No gradients, no glow. */
.ui-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border: 1px solid transparent; cursor: pointer;
  font-weight: var(--fw-semibold); white-space: nowrap; border-radius: var(--radius-md); text-decoration: none; line-height: 1;
  -webkit-user-select: none; user-select: none; -webkit-tap-highlight-color: transparent;
  transition: background var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease),
    box-shadow var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease); }
.ui-btn__ic { flex: none; } .ui-btn__chev { flex: none; margin-right: -3px; opacity: 0.8; }
.ui-btn:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.ui-btn:active:not(:disabled) { transform: translateY(0.5px); }
.ui-btn--sm { height: 30px; padding: 0 11px; font-size: var(--fs-sm); border-radius: var(--radius-sm); }
.ui-btn--md { height: 36px; padding: 0 15px; font-size: var(--fs-md); }
.ui-btn--lg { height: 44px; padding: 0 20px; font-size: var(--fs-md); border-radius: 12px; }
.ui-btn--block { width: 100%; }

/* filled — primary (blue = the system) */
.ui-btn--primary { background: var(--grad-primary, var(--c-primary)); color: var(--c-on-primary);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.22), 0 6px 18px -8px color-mix(in srgb, var(--c-primary) 70%, transparent); }
.ui-btn--primary:hover:not(:disabled) { filter: brightness(1.07); }
.ui-btn--primary:active:not(:disabled) { filter: brightness(0.95); }

/* filled — action (orange = your turn) */
.ui-btn--action { background: var(--c-action); color: var(--c-on-action); }
.ui-btn--action:hover:not(:disabled) { background: var(--c-action-hover); }
.ui-btn--action:active:not(:disabled) { background: var(--c-action-hover); }

/* secondary — a quiet filled neutral */
.ui-btn--tint { background: var(--c-fill); color: var(--c-text); border-color: transparent; box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05); }
.ui-btn--tint:hover:not(:disabled) { background: var(--c-fill-2); }
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
