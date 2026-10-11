<script setup>
defineProps({ modelValue: Boolean, label: { type: String, required: true } });
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <button type="button" role="switch" :aria-checked="modelValue" :aria-label="label"
          :class="['ui-switch', { on: modelValue }]" @click="emit('update:modelValue', !modelValue)" />
</template>
<style scoped>
.ui-switch { position: relative; width: 36px; height: 20px; flex: none; border: 0; border-radius: var(--radius-pill);
  background: var(--c-fill-2); cursor: pointer; transition: background var(--dur) var(--ease); }
.ui-switch::after { content: ""; position: absolute; left: 2px; top: 2px; width: 16px; height: 16px; border-radius: 50%;
  background: #fff; transition: transform var(--dur) var(--ease); }
.ui-switch.on { background: var(--c-primary); }
.ui-switch.on::after { transform: translateX(16px); }
</style>
