<script setup>
defineProps({ severity: String });
</script>
<template>
  <UiPill v-if="severity === 'critical'" tone="solid-bad">Critical</UiPill>
  <UiPill v-else-if="severity === 'major'" tone="solid-warn">Major</UiPill>
  <UiPill v-else>Minor</UiPill>
</template>
