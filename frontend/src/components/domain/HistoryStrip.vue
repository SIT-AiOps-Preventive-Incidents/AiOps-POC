<script setup>
// Last N days as small bars, one per day: grey = no incident, red = an incident was detected that day.
// The same idea as a public status page's uptime bars, built from the real incident history.
import { computed } from "vue";
const props = defineProps({ incidents: { type: Array, default: () => [] }, days: { type: Number, default: 7 } });
const DAY = 86400;
const bars = computed(() => {
  const start = new Date(); start.setHours(0, 0, 0, 0);
  const today = start.getTime() / 1000;
  return Array.from({ length: props.days }, (_, k) => {
    const from = today - (props.days - 1 - k) * DAY;
    const hits = props.incidents.filter((i) => i.detected_at >= from && i.detected_at < from + DAY);
    const date = new Date(from * 1000).toLocaleDateString([], { weekday: "short", day: "numeric" });
    return { from, n: hits.length, label: `${date}: ${hits.length ? `${hits.length} incident${hits.length > 1 ? "s" : ""}` : "no incidents"}` };
  });
});
</script>
<template>
  <span class="strip" role="img" :aria-label="`Last ${days} days: ${bars.filter((b) => b.n).length} days with incidents`">
    <i v-for="b in bars" :key="b.from" :class="{ hit: b.n }" :title="b.label" />
  </span>
</template>
<style scoped>
.strip { display: inline-flex; gap: 2px; align-items: stretch; height: 18px; }
.strip i { width: 6px; border-radius: 1px; background: var(--c-ok); opacity: 0.55; }
.strip i.hit { background: var(--c-bad); opacity: 1; }
</style>
