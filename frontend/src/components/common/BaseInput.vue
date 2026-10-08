<script setup lang="ts">
defineOptions({ inheritAttrs: false });
const model = defineModel<string | number>({ default: "" });
withDefaults(
  defineProps<{ label?: string; disabled?: boolean; type?: string }>(),
  { label: "", disabled: false, type: "text" },
);
</script>

<template>
  <label class="input"
    ><span v-if="label" class="label">{{ label }}</span
    ><input
      v-model="model"
      class="field"
      :disabled="disabled"
      :type="type"
      v-bind="$attrs"
  /></label>
</template>

<style scoped>
.input {
  display: block;
}
.input:has(input:disabled) {
  opacity: 0.5;
}
</style>
