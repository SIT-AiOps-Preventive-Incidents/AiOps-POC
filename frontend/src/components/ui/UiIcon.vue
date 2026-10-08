<script setup>
// Microsoft Fluent UI System Icons (MIT), vendored in /public/icons/f. Rendered as a CSS mask so the
// icon takes the current text colour - one icon file works on any background.
defineProps({ name: { type: String, required: true }, filled: Boolean, size: { type: Number, default: 20 } });
</script>
<template>
  <span class="ui-icon" aria-hidden="true"
        :style="{ '--i': `url(/icons/f/${name}_${filled ? 'filled' : 'regular'}.svg)`, width: `${size}px`, height: `${size}px` }" />
</template>
<style scoped>
.ui-icon { display: inline-block; flex: none; background: currentColor;
  -webkit-mask: var(--i) center / contain no-repeat; mask: var(--i) center / contain no-repeat; }
</style>
