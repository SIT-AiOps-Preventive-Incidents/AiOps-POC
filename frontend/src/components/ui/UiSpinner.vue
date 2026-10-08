<script setup>
defineProps({ size: { type: Number, default: 20 } });
</script>
<template>
  <span class="ui-spinner" role="progressbar" aria-label="Loading" :style="{ width: `${size}px`, height: `${size}px` }" />
</template>
<style scoped>
.ui-spinner { display: inline-block; flex: none; border: 2.5px solid var(--c-fill-2); border-top-color: var(--c-primary);
  border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
