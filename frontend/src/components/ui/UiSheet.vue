<script setup>
// Modal sheet: centered card on desktop, bottom sheet on phones. Closes on backdrop click or Escape.
import { onBeforeUnmount, watch } from "vue";
import UiIcon from "./UiIcon.vue";
const props = defineProps({ modelValue: Boolean, title: String, width: { type: Number, default: 520 } });
const emit = defineEmits(["update:modelValue"]);
const onKey = (e) => e.key === "Escape" && emit("update:modelValue", false);
watch(() => props.modelValue, (open) => (open ? addEventListener("keydown", onKey) : removeEventListener("keydown", onKey)));
onBeforeUnmount(() => removeEventListener("keydown", onKey));
</script>
<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="modelValue" class="ui-sheet" @click.self="emit('update:modelValue', false)">
        <div class="ui-sheet__box" role="dialog" aria-modal="true" :aria-label="title" :style="{ width: `min(${width}px, 100%)` }">
          <button class="ui-sheet__x" aria-label="Close" @click="emit('update:modelValue', false)"><UiIcon name="dismiss" :size="16" /></button>
          <h2 v-if="title" class="ui-sheet__title">{{ title }}</h2>
          <slot />
          <div v-if="$slots.footer" class="ui-sheet__foot"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
<style scoped>
.ui-sheet { position: fixed; inset: 0; background: var(--c-overlay); overscroll-behavior: contain; display: flex; align-items: center; justify-content: center; z-index: 50; padding: 24px; }
.ui-sheet__box { position: relative; background: var(--c-surface); border-radius: var(--radius-xl); box-shadow: var(--shadow-2); padding: 24px; max-height: 88vh; overflow: auto; }
.ui-sheet__title { font-size: var(--fs-xl); font-weight: var(--fw-bold); margin-bottom: 6px; padding-right: 36px; }
.ui-sheet__x { position: absolute; right: 14px; top: 14px; width: 30px; height: 30px; border-radius: 50%; border: 0; background: var(--c-fill-2); color: var(--c-text-2); display: grid; place-items: center; cursor: pointer; }
.ui-sheet__foot { display: flex; gap: 8px; justify-content: flex-end; margin-top: 18px; }
.sheet-enter-active, .sheet-leave-active { transition: opacity var(--dur) var(--ease); }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }
@media (max-width: 760px) { .ui-sheet { align-items: flex-end; padding: 0; } .ui-sheet__box { border-radius: var(--radius-xl) var(--radius-xl) 0 0; width: 100% !important; } }
</style>
