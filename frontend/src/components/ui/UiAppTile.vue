<script setup>
// App-icon tile: a real logo, or the pastel glyph for what it is, on a soft dark tile, with an optional status dot.
// `icon` takes the old icon names and maps them onto glyphs, so older callers get the drawn set without changes.
import { computed } from "vue";
import UiGlyph from "./UiGlyph.vue";
import UiLogo from "./UiLogo.vue";
const props = defineProps({ logo: String, icon: { type: String, default: "cube" }, color: String, status: String, size: { type: Number, default: 30 } });
const GLYPH = { server: "server", laptop: "laptop", globe: "globe", cube: "cube", apps: "service", database: "device", shield: "router",
  hard_drive: "device", cloud: "cloud", flash: "flash", book: "book", sparkle: "sparkle", warning: "warning", wrench: "wrench", pulse: "pulse" };
const glyph = computed(() => GLYPH[props.icon] || props.icon);
</script>
<template>
  <span class="ui-tile" :style="{ width: `${size}px`, height: `${size}px`, borderRadius: `${Math.round(size * 0.3)}px` }">
    <UiLogo v-if="logo" :name="logo" :size="Math.round(size * 0.62)" />
    <UiGlyph v-else :name="glyph" :size="Math.round(size * 0.66)" />
    <span v-if="status" :class="['ui-tile__dot', `tone-${status}`]" />
  </span>
</template>
<style scoped>
.ui-tile { position: relative; display: grid; place-items: center; flex: none; background: var(--c-fill);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05); }
.ui-tile__dot { position: absolute; right: -3px; bottom: -3px; width: 10px; height: 10px; border-radius: 50%; border: 2px solid var(--c-surface); background: var(--c-neutral); }
.tone-ok { background: var(--c-ok); } .tone-bad { background: var(--c-bad); } .tone-warn { background: var(--c-warn); }
</style>
