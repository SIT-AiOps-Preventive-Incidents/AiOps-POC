<script setup>
import AppSidebar from "@/components/layout/AppSidebar.vue";
import AppTopBar from "@/components/layout/AppTopBar.vue";
import CommandPalette from "@/components/layout/CommandPalette.vue";
import { usePolling } from "@/composables/usePolling";
import { watch } from "vue";
import { useRoute } from "vue-router";
import { useAppStore } from "@/stores/app";
import { useAuthStore } from "@/stores/auth";

const app = useAppStore();
const auth = useAuthStore();
const route = useRoute();
usePolling(() => (auth.me ? app.load() : null), 15000); // global status for sidebar badge + top bar, shared by every page
watch(() => auth.me?.id, (id) => id && app.load());     // ...loaded the moment someone signs in
</script>
<template>
  <template v-if="route.meta.bare">
    <router-view class="bare" />
    <UiToastHost />
  </template>
  <template v-else-if="auth.me">
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
</template>
<style>
/* the app sits in one rounded frame on a darker ground; the sidebar is a panel inside it */
/* the ground: near-black with two faint sweeping lines, like the reference; the app is a framed glass panel on it */
body { background: var(--c-bg); }
#app { display: flex; overflow: hidden; padding: 12px; gap: 12px; background: var(--c-frame); position: relative; isolation: isolate; }
#app::before { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none; opacity: var(--ground-lines, 1);
  background: radial-gradient(120% 70% at 85% -10%, rgba(255, 255, 255, 0.045), transparent 60%),
    url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 1000' preserveAspectRatio='none'><path d='M-50 1050 C 500 640 900 520 1650 180' fill='none' stroke='white' stroke-opacity='0.05' stroke-width='1.2'/><path d='M300 -40 C 700 260 1200 420 1660 470' fill='none' stroke='white' stroke-opacity='0.035' stroke-width='1'/></svg>") center / 100% 100% no-repeat; }
.bare { flex: 1; margin: -12px; }
.main { flex: 1; display: flex; flex-direction: column; min-width: 0; height: calc(100vh - 24px); position: relative; }
.guide-off .ui-ph__sub { display: none; }
.view { flex: 1; overflow: auto; padding: 0 20px 64px 8px; }
.view > .page > .ui-ph:first-child, .view > .page > :first-child .ui-ph { margin-top: 4px; }
@media (max-width: 760px) { #app { padding: 0; gap: 0; } .main { height: 100vh; } .view { padding: 4px 16px 80px; } }
</style>
