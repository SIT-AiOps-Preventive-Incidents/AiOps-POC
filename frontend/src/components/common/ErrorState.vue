<script setup lang="ts">
defineProps<{ message: string }>();
defineEmits<{ retry: [] }>();
</script>
<template>
  <div class="state" role="alert">
    <strong>Couldn’t load this page</strong>
    <p>{{ message }}</p>
    <button class="link" type="button" @click="$emit('retry')">
      Try again
    </button>
  </div>
</template>
<style scoped>
.state {
  display: grid;
  min-height: 180px;
  place-items: center;
  align-content: center;
  gap: 8px;
  border: 1px solid var(--color-status-danger-bg);
  border-radius: var(--radius-md);
  background: white;
  color: var(--color-text-muted);
  text-align: center;
}
.state strong {
  color: var(--color-status-danger-text);
}
.state p {
  margin: 0;
}
.state button {
  border: 0;
  background: none;
}
</style>
