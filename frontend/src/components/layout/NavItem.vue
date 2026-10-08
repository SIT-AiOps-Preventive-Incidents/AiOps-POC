<script setup lang="ts">
import { RouterLink } from "vue-router";
import AppIcon from "@/components/common/AppIcon.vue";
defineProps<{ to: string; label: string; icon: string; badge?: number }>();
</script>
<template>
  <RouterLink class="nav-item" :to="to" @click="$emit('navigate')"
    ><AppIcon :name="icon" :size="16" /><span>{{ label }}</span
    ><b v-if="badge" class="count">{{ badge }}</b></RouterLink
  >
</template>
<style scoped>
.nav-item {
  display: flex;
  width: 168px;
  height: 36px;
  align-items: center;
  gap: 10px;
  border-radius: 6px;
  padding: 8px 10px;
  font-size: 11px;
  line-height: normal;
  color: var(--color-text-default);
}
.nav-item:hover {
  background: var(--color-status-info-bg);
}
.nav-item.router-link-active {
  background: var(--color-accent-primary);
  color: white;
  font-weight: 500;
}
.nav-item.router-link-active :deep(img) {
  filter: brightness(0) invert(1);
}
.count {
  margin-left: auto;
  border-radius: 999px;
  background: var(--color-status-danger);
  color: white;
  padding: 0 6px;
  font-size: 10px;
}
</style>
