<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";
import AppSidebar from "./AppSidebar.vue";
import AppTopbar from "./AppTopbar.vue";
import { useSystemStore } from "@/stores/system";
const system = useSystemStore();
let timer: number | undefined;
onMounted(() => {
  void system.refresh();
  timer = window.setInterval(() => {
    if (!document.hidden) void system.refresh();
  }, 20000);
});
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer);
});
</script>
<template>
  <div class="shell">
    <AppSidebar />
    <main>
      <AppTopbar />
      <div class="content"><RouterView /></div>
    </main>
  </div>
</template>
<style scoped>
.shell {
  min-height: 100vh;
}
.shell main {
  min-height: 100vh;
  margin-left: var(--sidebar-width);
}
.content {
  padding: 24px 28px 72px;
}
@media (max-width: 760px) {
  .shell main {
    margin-left: 0;
  }
  .content {
    padding: 20px 16px 56px;
  }
}
</style>
