<script setup>
defineProps({ modelValue: Boolean, label: { type: String, required: true } });
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <button type="button" role="switch" :aria-checked="modelValue" :aria-label="label"
          :class="['ui-switch', { on: modelValue }]" @click="emit('update:modelValue', !modelValue)" />
</template>
<style scoped>
.ui-switch { position: relative; width: 51px; height: 31px; flex: none; border: 0; border-radius: var(--radius-pill);
  background: var(--c-fill-2); cursor: pointer; transition: background var(--dur) var(--ease); }
.ui-switch::after { content: ""; position: absolute; left: 2px; top: 2px; width: 27px; height: 27px; border-radius: 50%;
  background: #fff; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2); transition: transform var(--dur) var(--ease); }
.ui-switch.on { background: var(--c-ok); }
.ui-switch.on::after { transform: translateX(20px); }
</style>
