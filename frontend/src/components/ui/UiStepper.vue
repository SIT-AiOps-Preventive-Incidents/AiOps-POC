<script setup>
// Horizontal progress: steps = [{ label, time, state: 'done' | 'current' | 'failed' | 'todo' }]
// The connector runs between circles (never through them); the check/cross are stroked so they stay crisp at 28px.
defineProps({ steps: { type: Array, required: true } });
</script>
<template>
  <ol class="ui-stepper" aria-label="Progress">
    <li v-for="(s, i) in steps" :key="s.label" :class="['ui-step', s.state]"
        :aria-current="s.state === 'current' ? 'step' : undefined">
      <span class="ui-step__c">
        <svg v-if="s.state === 'done'" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else-if="s.state === 'failed'" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
          <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
        </svg>
        <span v-else-if="s.state === 'current'" class="ui-step__dot" />
        <template v-else>{{ i + 1 }}</template>
      </span>
      <span class="ui-step__l">{{ s.label }}</span>
      <span class="ui-step__t">{{ s.time }}</span>
    </li>
  </ol>
</template>
<style scoped>
.ui-stepper { --c: 28px; --gap: 6px; display: flex; list-style: none; margin: 0; padding: 16px 12px; background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); }
.ui-step { flex: 1; display: flex; flex-direction: column; align-items: center; text-align: center; position: relative; min-width: 0; }
/* connector from the previous circle's right edge to this circle's left edge */
.ui-step::before { content: ""; position: absolute; top: calc(var(--c) / 2 - 1px); height: 2px; border-radius: 1px;
  left: calc(-50% + var(--c) / 2 + var(--gap)); right: calc(50% + var(--c) / 2 + var(--gap)); background: var(--c-fill-2); }
.ui-step:first-child::before { display: none; }
.ui-step.done::before, .ui-step.current::before, .ui-step.failed::before { background: var(--c-primary); }
.ui-step__c { width: var(--c); height: var(--c); box-sizing: border-box; border-radius: 50%; background: var(--c-fill-2); color: var(--c-text-3);
  display: grid; place-items: center; font-size: 13px; font-weight: var(--fw-bold); font-variant-numeric: tabular-nums; }
.done .ui-step__c { background: var(--c-primary); color: #fff; }
.current .ui-step__c { background: var(--c-surface); border: 2px solid var(--c-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--c-primary) 16%, transparent); }
.ui-step__dot { width: 10px; height: 10px; border-radius: 50%; background: var(--c-primary); }
.failed .ui-step__c { background: var(--c-bad); color: #fff; }
.ui-step__l { font-size: 12.5px; font-weight: var(--fw-semibold); margin-top: 8px; text-wrap: balance; }
.todo .ui-step__l { color: var(--c-text-3); font-weight: var(--fw-medium, 500); }
.current .ui-step__l { color: var(--c-primary); }
.ui-step__t { font-size: var(--fs-xs); color: var(--c-text-3); font-variant-numeric: tabular-nums; min-height: 1em; }
@media (max-width: 760px) { .ui-step__t { display: none; } .ui-step__l { font-size: 11px; } .ui-stepper { --gap: 3px; } }
</style>
