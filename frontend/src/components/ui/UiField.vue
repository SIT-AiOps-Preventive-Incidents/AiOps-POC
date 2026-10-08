<script setup>
import { useId } from "vue";
defineProps({ modelValue: [String, Number], label: String, hint: String, placeholder: String, type: { type: String, default: "text" },
  multiline: Boolean, mono: Boolean, autocomplete: { type: String, default: "off" } });
const emit = defineEmits(["update:modelValue", "enter"]);
const id = useId();
</script>
<template>
  <div class="ui-field">
    <label v-if="label" :for="id">{{ label }} <span v-if="hint" class="ui-field__hint">{{ hint }}</span></label>
    <textarea v-if="multiline" :id="id" :value="modelValue" :placeholder="placeholder" rows="2"
              @input="emit('update:modelValue', $event.target.value)" />
    <input v-else :id="id" :type="type" :value="modelValue" :placeholder="placeholder" :autocomplete="autocomplete"
           spellcheck="false" :class="{ mono }" @input="emit('update:modelValue', $event.target.value)" @keydown.enter="emit('enter')">
  </div>
</template>
<style scoped>
.ui-field label { display: block; font-size: var(--fs-sm); color: var(--c-text-2); margin: 12px 0 6px; font-weight: var(--fw-medium); }
.ui-field__hint { color: var(--c-text-3); font-weight: var(--fw-regular); }
input, textarea { width: 100%; background: var(--c-fill); border: 1px solid transparent; border-radius: var(--radius-md); padding: 10px 12px; font-size: var(--fs-md); }
input:focus, textarea:focus { outline: none; border-color: var(--c-primary); background: var(--c-surface); box-shadow: var(--focus-ring); }
input.mono { font-family: var(--font-mono); font-size: 14px; }
</style>
