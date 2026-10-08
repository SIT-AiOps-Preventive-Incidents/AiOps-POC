<script setup>
import { ref } from "vue";
import { useClipboard } from "@/composables/useClipboard";
const props = defineProps({ code: { type: String, required: true } });
const el = ref(null);
const { copy } = useClipboard();
</script>
<template>
  <div class="ui-code"><span ref="el">{{ code }}</span><button type="button" @click="copy(props.code, el)">Copy</button></div>
</template>
<style scoped>
.ui-code { position: relative; background: var(--c-code-bg); color: var(--c-code-text); border-radius: 12px; padding: 14px 76px 14px 16px;
  font: 13px/1.6 var(--font-mono); white-space: pre-wrap; word-break: break-all; }
button { position: absolute; top: 8px; right: 8px; background: rgba(255, 255, 255, 0.14); color: #fff; border: 0; border-radius: 7px;
  font: var(--fw-semibold) 12px var(--font); padding: 5px 10px; cursor: pointer; }
button:hover { background: rgba(255, 255, 255, 0.24); }
</style>
