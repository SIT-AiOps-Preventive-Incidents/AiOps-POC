<script setup>
import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppTopBar from "@/components/layout/AppTopBar.vue";
import { usePolling } from "@/composables/usePolling";
import { useAppStore } from "@/stores/app";

const app = useAppStore();
usePolling(() => app.load(), 15000); // global status for sidebar badge + top bar, shared by every page
</script>
<template>
  <AppSidebar />
  <main class="main">
    <AppTopBar />
    <div class="view">
      <router-view v-slot="{ Component, route }">
        <component :is="Component" :key="route.fullPath" />
      </router-view>
    </div>
  </main>
  <UiToastHost />
</template>
<style>
#app { display: flex; overflow: hidden; }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; height: 100vh; }
.view { flex: 1; overflow: auto; padding: 8px 32px 80px; }
@media (max-width: 760px) { .view { padding: 4px 16px 80px; } }
</style>
