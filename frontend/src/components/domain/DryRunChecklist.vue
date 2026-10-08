<script setup>
// What the dry run checked, what it would change, and who would notice - nothing here has been applied.
defineProps({ dryRun: Object });
</script>
<template>
  <div v-if="dryRun" class="dr">
    <div class="dr__head">Dry run <span :class="dryRun.ok ? 'ok' : 'bad'">{{ dryRun.ok ? "passed" : "failed" }}</span>
      <span class="muted"> · nothing has been changed yet</span></div>
    <ul class="dr__checks">
      <li v-for="c in dryRun.checks" :key="c.name" :class="c.ok ? 'y' : 'n'">
        <span class="dr__m"><UiIcon :name="c.ok ? 'checkmark' : 'dismiss'" :size="13" /></span>
        <span>{{ c.name }}<span class="dr__d">{{ c.detail }}</span></span>
      </li>
    </ul>
    <UiDisclosure v-if="dryRun.changes?.length" :card="false" :title="`What will change (${dryRun.changes.length})`">
      <pre class="dr__pre">{{ dryRun.changes.join("\n") }}</pre>
    </UiDisclosure>
    <div v-if="dryRun.impact" class="small mt-2"><span class="muted">Impact:</span> {{ dryRun.impact }}</div>
  </div>
</template>
<style scoped>
.dr__head { font-size: var(--fs-sm); font-weight: var(--fw-semibold); }
.dr__checks { list-style: none; padding: 0; margin: 12px 0; display: flex; flex-direction: column; gap: 8px; }
.dr__checks li { display: flex; gap: 10px; align-items: flex-start; font-size: 14px; }
.dr__m { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; flex: none; color: #fff; margin-top: 1px; }
.y .dr__m { background: var(--c-ok); } .n .dr__m { background: var(--c-bad); }
.dr__d { display: block; font-size: 12.5px; color: var(--c-text-2); }
.dr__pre { background: var(--c-fill); border-radius: 10px; padding: 10px 12px; font: 12px/1.5 var(--font-mono); white-space: pre-wrap; margin: 8px 0 0; }
</style>
