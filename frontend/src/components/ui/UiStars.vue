<script setup>
defineProps({ modelValue: { type: Number, default: 0 } });
const emit = defineEmits(["update:modelValue"]);
</script>
<template>
  <div class="ui-stars" role="radiogroup" aria-label="Rating">
    <button v-for="n in 5" :key="n" type="button" role="radio" :aria-checked="modelValue === n" :aria-label="`${n} stars`"
            :class="{ on: n <= modelValue }" @click="emit('update:modelValue', n)">&#9733;</button>
  </div>
</template>
<style scoped>
.ui-stars { display: flex; gap: 4px; }
button { background: none; border: 0; font-size: 28px; line-height: 1; color: var(--c-fill-2); cursor: pointer; padding: 0 2px; }
button.on { color: var(--c-star); }
</style>
