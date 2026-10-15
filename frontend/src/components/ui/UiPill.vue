<script setup>
// tone: ok bad warn ai info neutral action solid-bad solid-warn
// A small dot carries the status colour next to the label - clean and uniform, no mixed geometry.
// mark=false for plain labels; solid tones already read as a filled chip, so they skip the dot.
import { computed } from "vue";
const props = defineProps({ tone: { type: String, default: "neutral" }, mark: { type: Boolean, default: true } });
const dot = computed(() => props.mark && props.tone !== "neutral" && !props.tone.startsWith("solid-"));
</script>
<template>
  <span :class="['ui-pill', `ui-pill--${tone}`]">
    <span v-if="dot" class="ui-pill__dot" aria-hidden="true" />
    <slot />
  </span>
</template>
<style scoped>
.ui-pill { display: inline-flex; align-items: center; gap: 5px; font-size: var(--fs-xs); font-weight: var(--fw-semibold); line-height: 18px; padding: 1px 8px; border-radius: var(--radius-pill); white-space: nowrap; }
.ui-pill__dot { flex: none; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.ui-pill--neutral { background: var(--c-fill); color: var(--c-text-2); }
.ui-pill--ok { background: var(--c-ok-bg); color: var(--c-ok-text); }
.ui-pill--bad { background: var(--c-bad-bg); color: var(--c-bad-text); }
.ui-pill--warn { background: var(--c-warn-bg); color: var(--c-warn-text); }
.ui-pill--ai, .ui-pill--info { background: var(--c-info-bg); color: var(--c-info-text); }
.ui-pill--action { background: var(--c-action); color: var(--c-on-action); }
.ui-pill--solid-bad { background: var(--c-bad); color: #fff; }
.ui-pill--solid-warn { background: var(--c-warn); color: #1a1300; }
</style>
