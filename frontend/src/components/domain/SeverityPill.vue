<script setup>
defineProps({ severity: String });
</script>
<template>
  <!-- severity is metadata (how bad), shown as a quiet tinted label so it never competes with the one
       orange call-to-action (Review fix / your turn). Colour + shape still carry the level. -->
  <UiPill v-if="severity === 'critical'" tone="bad">Critical</UiPill>
  <UiPill v-else-if="severity === 'major'" tone="warn">Major</UiPill>
  <UiPill v-else>Minor</UiPill>
</template>
