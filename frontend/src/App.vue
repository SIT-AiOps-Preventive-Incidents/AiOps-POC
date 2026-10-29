<script setup>
import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppTopBar from "@/components/layout/AppTopBar.vue";
import CommandPalette from "@/components/layout/CommandPalette.vue";
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
  <CommandPalette />
  <UiToastHost />
</template>
<style>
/* the app sits in one rounded frame on a darker ground; the sidebar is a panel inside it */
#app { display: flex; overflow: hidden; padding: 12px; gap: 12px; background: var(--c-frame); }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; height: calc(100vh - 24px); }
.view { flex: 1; overflow: auto; padding: 0 20px 64px 8px; }
@media (max-width: 760px) { #app { padding: 0; gap: 0; } .main { height: 100vh; } .view { padding: 4px 16px 80px; } }
</style>
