<script setup>
defineProps({ modelValue: Boolean, label: { type: String, required: true } });
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <button type="button" role="switch" :aria-checked="modelValue" :aria-label="label"
          :class="['ui-switch', { on: modelValue }]" @click="emit('update:modelValue', !modelValue)" />
</template>
<style scoped>
.ui-switch { position: relative; width: 46px; height: 26px; flex: none; border: 0; border-radius: var(--radius-pill);
  background: var(--c-fill-2); cursor: pointer; transition: background var(--dur) var(--ease); }
.ui-switch::after { content: ""; position: absolute; left: 3px; top: 3px; width: 20px; height: 20px; border-radius: 50%; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
  background: #fff; transition: transform var(--dur) var(--ease); }
.ui-switch.on { background: var(--grad-primary, var(--c-primary)); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12); }
.ui-switch.on::after { transform: translateX(20px); }
</style>
