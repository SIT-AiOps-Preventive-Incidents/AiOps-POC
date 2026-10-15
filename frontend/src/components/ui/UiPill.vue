<script setup>
// tone: ok bad warn ai info neutral action solid-bad solid-warn
// Every status carries a shape as well as a colour (WCAG 1.4.1): circle-check = ok, square = bad,
// triangle = warning, diamond = your turn, dot = system working. mark=false for plain labels.
defineProps({ tone: { type: String, default: "neutral" }, mark: { type: Boolean, default: true } });
</script>
<template>
  <span :class="['ui-pill', `ui-pill--${tone}`]">
    <svg v-if="mark && tone !== 'neutral'" class="ui-pill__m" viewBox="0 0 10 10" width="10" height="10" aria-hidden="true">
      <template v-if="tone === 'ok'"><circle cx="5" cy="5" r="4.5" fill="currentColor" /><path d="M2.8 5.2l1.5 1.5 2.9-3.2" fill="none" stroke="var(--c-ok-bg)" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" /></template>
      <rect v-else-if="tone.endsWith('bad')" x="1" y="1" width="8" height="8" rx="1" fill="currentColor" />
      <path v-else-if="tone.endsWith('warn')" d="M5 0.8L9.6 9H0.4z" fill="currentColor" />
      <path v-else-if="tone === 'action'" d="M5 0.5L9.5 5L5 9.5L0.5 5z" fill="currentColor" />
      <circle v-else cx="5" cy="5" r="3" fill="currentColor" />
    </svg>
    <slot />
  </span>
</template>
<style scoped>
.ui-pill { display: inline-flex; align-items: center; gap: 5px; font-size: var(--fs-xs); font-weight: var(--fw-semibold); line-height: 18px; padding: 1px 7px; border-radius: var(--radius-sm); white-space: nowrap; }
.ui-pill__m { flex: none; }
.ui-pill--neutral { background: var(--c-fill); color: var(--c-text-2); }
.ui-pill--ok { background: var(--c-ok-bg); color: var(--c-ok-text); }
.ui-pill--bad { background: var(--c-bad-bg); color: var(--c-bad-text); }
.ui-pill--warn { background: var(--c-warn-bg); color: var(--c-warn-text); }
.ui-pill--ai, .ui-pill--info { background: var(--c-info-bg); color: var(--c-info-text); }
.ui-pill--action { background: var(--c-action); color: var(--c-on-action); }
.ui-pill--solid-bad { background: var(--c-bad); color: #fff; }
.ui-pill--solid-warn { background: var(--c-warn); color: #1a1300; }
</style>
