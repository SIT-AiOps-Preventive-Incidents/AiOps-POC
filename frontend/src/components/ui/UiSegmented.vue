<script setup>
// Button group for one choice. options: [{ value, label, logo?, icon? }]
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
.ui-seg { display: inline-flex; flex-wrap: wrap; border: 1px solid var(--c-border); border-radius: var(--radius-md); overflow: hidden; }
.ui-seg button { display: inline-flex; align-items: center; gap: 6px; border: 0; background: var(--c-surface); padding: 6px 12px;
  font-size: var(--fs-sm); font-weight: var(--fw-medium); color: var(--c-text-2); cursor: pointer; touch-action: manipulation; }
.ui-seg button + button { border-left: 1px solid var(--c-border); }
.ui-seg button:hover { background: var(--c-fill); }
.ui-seg button.on { background: var(--c-primary-tint); color: var(--c-primary); }
</style>
