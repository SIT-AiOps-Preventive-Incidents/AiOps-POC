<script setup>
// Horizontal progress: steps = [{ label, time, state: 'done' | 'current' | 'you' | 'failed' | 'todo' }] ('you' = a person must act, orange)
// The connector runs between circles (never through them); the check/cross are stroked so they stay crisp at 28px.
defineProps({ steps: { type: Array, required: true } });
</script>
<template>
  <ol class="ui-stepper" aria-label="Progress">
    <li v-for="(s, i) in steps" :key="s.label" :class="['ui-step', s.state, { 'has-tip': s.hint }]"
        :aria-current="['current', 'you'].includes(s.state) ? 'step' : undefined">
      <span v-if="s.hint" class="ui-step__tip" role="tooltip">{{ s.hint }}</span>
      <span class="ui-step__c">
        <svg v-if="s.state === 'done'" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
          <path d="M3.5 8.5l3 3 6-7" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <svg v-else-if="s.state === 'failed'" viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
          <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
        </svg>
        <span v-else-if="s.state === 'current' || s.state === 'you'" class="ui-step__dot" />
        <template v-else>{{ i + 1 }}</template>
      </span>
      <span class="ui-step__l">{{ s.label }}</span>
      <span class="ui-step__t">{{ s.time }}</span>
    </li>
  </ol>
</template>
<style scoped>
.ui-stepper { --c: 28px; --gap: 6px; display: flex; list-style: none; margin: 0; padding: 16px 12px; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); }
.ui-step { flex: 1; display: flex; flex-direction: column; align-items: center; text-align: center; position: relative; min-width: 0; }
/* connector from the previous circle's right edge to this circle's left edge */
.ui-step::before { content: ""; position: absolute; top: calc(var(--c) / 2 - 1px); height: 2px; border-radius: 1px;
  left: calc(-50% + var(--c) / 2 + var(--gap)); right: calc(50% + var(--c) / 2 + var(--gap)); background: var(--c-fill-2); }
.ui-step:first-child::before { display: none; }
.ui-step.done::before, .ui-step.current::before, .ui-step.you::before, .ui-step.failed::before { background: var(--c-primary); }
.ui-step__c { width: var(--c); height: var(--c); box-sizing: border-box; border-radius: 50%; background: var(--c-fill-2); color: var(--c-text-3);
  display: grid; place-items: center; font-size: 13px; font-weight: var(--fw-bold); font-variant-numeric: tabular-nums; }
.done .ui-step__c { background: var(--c-primary); color: #fff; }
.current .ui-step__c { background: var(--c-surface); border: 2px solid var(--c-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--c-primary) 16%, transparent); }
.ui-step__dot { width: 10px; height: 10px; border-radius: 50%; background: var(--c-primary); }
.failed .ui-step__c { background: var(--c-bad); color: #fff; }
.ui-step__l { font-size: 12.5px; font-weight: var(--fw-semibold); margin-top: 8px; text-wrap: balance; }
.todo .ui-step__l { color: var(--c-text-3); font-weight: var(--fw-medium, 500); }
.current .ui-step__l { color: var(--c-primary); }
.you .ui-step__c { background: var(--c-surface); border: 2px solid var(--c-action); box-shadow: 0 0 0 4px color-mix(in srgb, var(--c-action) 18%, transparent); }
.you .ui-step__dot { background: var(--c-action); }
.you .ui-step__l { color: var(--c-action-text); }
.ui-step__t { font-size: var(--fs-xs); color: var(--c-text-3); font-variant-numeric: tabular-nums; min-height: 1em; }
/* hover detail */
.ui-step.has-tip { cursor: help; }
.ui-step__tip { position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%) translateY(4px);
  width: max-content; max-width: 240px; padding: 7px 10px; border-radius: var(--radius-md); background: var(--c-toast); color: var(--c-on-toast);
  font-size: var(--fs-xs); font-weight: var(--fw-medium); line-height: var(--lh-snug); text-align: left; box-shadow: var(--shadow-2);
  opacity: 0; pointer-events: none; transition: opacity var(--dur-fast) var(--ease), transform var(--dur-fast) var(--ease); z-index: 5; white-space: normal; }
.ui-step__tip::after { content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%); border: 5px solid transparent; border-top-color: var(--c-toast); }
.ui-step.has-tip:hover .ui-step__tip, .ui-step.has-tip:focus-within .ui-step__tip { opacity: 1; transform: translateX(-50%) translateY(0); }
@media (prefers-reduced-motion: reduce) { .ui-step__tip { transition: none; } }
@media (max-width: 760px) { .ui-step__t { display: none; } .ui-step__l { font-size: 11px; } .ui-stepper { --gap: 3px; } }
</style>
