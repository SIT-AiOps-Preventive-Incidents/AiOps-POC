<script setup lang="ts">
import { useUiStore } from "@/stores/ui";
const props = defineProps<{ code: string }>();
const ui = useUiStore();
async function copy() {
  try {
    await navigator.clipboard.writeText(props.code);
    ui.notify("Copied");
  } catch {
    ui.notify("Copy failed — select the text manually");
  }
}
</script>
<template>
  <pre
    class="code-block"
  ><code>{{ code }}</code><button type="button" @click="copy">Copy</button></pre>
</template>
<style scoped>
pre {
  margin: 0;
}
button {
  position: absolute;
  right: 10px;
  top: 10px;
  border: 1px solid rgb(255 255 255 / 25%);
  border-radius: 6px;
  background: rgb(255 255 255 / 10%);
  color: white;
  padding: 4px 9px;
  cursor: pointer;
}
</style>
