<script setup lang="ts">
import AppShell from "@/components/layout/AppShell.vue";
import { useUiStore } from "@/stores/ui";
const ui = useUiStore();
</script>
<template>
  <AppShell /><Teleport to="body"
    ><div v-if="ui.toast" class="toast" role="status">
      {{ ui.toast }}
    </div></Teleport
  >
</template>
<style scoped>
.toast {
  position: fixed;
  z-index: 200;
  right: 20px;
  bottom: 20px;
  max-width: 360px;
  border-radius: var(--radius-md);
  background: var(--color-text-default);
  color: white;
  padding: 10px 14px;
  box-shadow: var(--shadow-dialog);
}
</style>
