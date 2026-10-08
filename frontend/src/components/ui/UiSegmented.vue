<script setup>
// iOS segmented control. options: [{ value, label, logo?, icon? }]
import UiIcon from "./UiIcon.vue";
import UiLogo from "./UiLogo.vue";
defineProps({ modelValue: [String, Number], options: { type: Array, required: true }, label: String });
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <div class="ui-seg" role="radiogroup" :aria-label="label">
    <button v-for="o in options" :key="o.value" type="button" role="radio" :aria-checked="modelValue === o.value"
            :class="{ on: modelValue === o.value }" @click="emit('update:modelValue', o.value)">
      <UiLogo v-if="o.logo" :name="o.logo" :size="16" /><UiIcon v-else-if="o.icon" :name="o.icon" :size="16" />{{ o.label }}
    </button>
  </div>
</template>
<style scoped>
.ui-seg { display: inline-flex; flex-wrap: wrap; gap: 2px; background: var(--c-fill-2); border-radius: 9px; padding: 2px; }
.ui-seg button { display: inline-flex; align-items: center; gap: 6px; border: 0; background: none; padding: 6px 14px; border-radius: 7px;
  font-size: 13.5px; font-weight: var(--fw-medium); color: var(--c-text); cursor: pointer; touch-action: manipulation; }
.ui-seg button.on { background: var(--c-surface); box-shadow: var(--shadow-seg); }
</style>
