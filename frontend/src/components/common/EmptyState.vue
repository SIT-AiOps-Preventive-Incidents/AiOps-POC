<script setup lang="ts">
withDefaults(defineProps<{ title?: string; message?: string }>(), {
  title: "Nothing here yet",
  message: "",
});
</script>
<template>
  <div class="state">
    <strong>{{ title }}</strong>
    <p v-if="message">{{ message }}</p>
    <slot />
  </div>
</template>
<style scoped>
.state {
  display: grid;
  min-height: 160px;
  place-items: center;
  align-content: center;
  gap: 6px;
  color: var(--color-text-muted);
  text-align: center;
}
.state strong {
  color: var(--color-text-default);
}
.state p {
  margin: 0;
}
</style>
