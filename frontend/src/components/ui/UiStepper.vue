<script setup>
// Horizontal progress: steps = [{ label, time, state: 'done' | 'current' | 'failed' | 'todo' }]
import UiIcon from "./UiIcon.vue";
defineProps({ steps: { type: Array, required: true } });
</script>
<template>
  <ol class="ui-stepper" aria-label="Progress">
    <li v-for="(s, i) in steps" :key="s.label" :class="['ui-step', s.state]">
      <span class="ui-step__c">
        <UiIcon v-if="s.state === 'done'" name="checkmark" :size="15" />
        <UiIcon v-else-if="s.state === 'failed'" name="dismiss" :size="15" />
        <template v-else>{{ i + 1 }}</template>
      </span>
      <span class="ui-step__l">{{ s.label }}</span>
      <span class="ui-step__t">{{ s.time }}</span>
    </li>
  </ol>
</template>
<style scoped>
.ui-stepper { display: flex; list-style: none; margin: 0; padding: 16px 12px; background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); }
.ui-step { flex: 1; display: flex; flex-direction: column; align-items: center; text-align: center; position: relative; min-width: 0; }
.ui-step::before { content: ""; position: absolute; top: 13px; left: -50%; width: 100%; height: 2px; background: var(--c-fill-2); }
.ui-step:first-child::before { display: none; }
.ui-step.done::before, .ui-step.current::before { background: var(--c-primary); }
.ui-step__c { width: 28px; height: 28px; border-radius: 50%; background: var(--c-fill-2); color: var(--c-text-3); display: grid; place-items: center; position: relative; font-size: 13px; font-weight: var(--fw-bold); }
.done .ui-step__c { background: var(--c-primary); color: #fff; }
.current .ui-step__c { background: var(--c-surface); border: 2.5px solid var(--c-primary); color: var(--c-primary); }
.failed .ui-step__c { background: var(--c-bad); color: #fff; }
.ui-step__l { font-size: 12.5px; font-weight: var(--fw-semibold); margin-top: 6px; }
.ui-step__t { font-size: var(--fs-xs); color: var(--c-text-3); font-variant-numeric: tabular-nums; min-height: 1em; }
@media (max-width: 760px) { .ui-step__t { display: none; } .ui-step__l { font-size: 11px; } }
</style>
