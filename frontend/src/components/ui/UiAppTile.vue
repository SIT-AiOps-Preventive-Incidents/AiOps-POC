<script setup>
// 30 px app-icon tile: a real logo on white, or a Fluent icon on a coloured square, with an optional status dot.
import UiIcon from "./UiIcon.vue";
import UiLogo from "./UiLogo.vue";
defineProps({ logo: String, icon: { type: String, default: "cube" }, color: String, status: String, size: { type: Number, default: 30 } });
</script>
<template>
  <span class="ui-tile" :class="{ 'ui-tile--logo': logo || !color }"
        :style="{ width: `${size}px`, height: `${size}px`, background: logo || !color ? undefined : color }">
    <UiLogo v-if="logo" :name="logo" :size="Math.round(size * 0.66)" />
    <UiIcon v-else :name="icon" :filled="!!color" :size="Math.round(size * 0.6)" />
    <span v-if="status" :class="['ui-tile__dot', `tone-${status}`]" />
  </span>
</template>
<style scoped>
.ui-tile { position: relative; border-radius: var(--radius-sm); display: grid; place-items: center; flex: none; color: #fff; }
.ui-tile--logo { background: var(--c-surface); color: var(--c-text-2); box-shadow: inset 0 0 0 0.5px var(--c-separator), 0 1px 2px rgba(0, 0, 0, 0.06); }
.ui-tile__dot { position: absolute; right: -3px; bottom: -3px; width: 11px; height: 11px; border-radius: 50%; border: 2px solid var(--c-surface); background: var(--c-neutral); }
.tone-ok { background: var(--c-ok); } .tone-bad { background: var(--c-bad); } .tone-warn { background: var(--c-warn); }
</style>
