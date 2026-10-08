<script setup lang="ts">
import BaseButton from "./BaseButton.vue";
defineProps<{
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  busy?: boolean;
}>();
defineEmits<{ confirm: []; cancel: [] }>();
</script>
<template>
  <Teleport to="body"
    ><div
      v-if="open"
      class="backdrop"
      role="presentation"
      @click.self="$emit('cancel')"
    >
      <section
        class="dialog"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
      >
        <h2>{{ title }}</h2>
        <p>{{ message }}</p>
        <div class="actions">
          <BaseButton variant="secondary" @click="$emit('cancel')"
            >Cancel</BaseButton
          ><BaseButton
            :variant="danger ? 'danger' : 'primary'"
            :disabled="busy"
            @click="$emit('confirm')"
            >{{ busy ? "Working…" : confirmLabel || "Confirm" }}</BaseButton
          >
        </div>
      </section>
    </div></Teleport
  >
</template>
<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  background: rgb(23 32 51 / 40%);
  padding: 20px;
}
.dialog {
  width: min(460px, 100%);
  border-radius: var(--radius-lg);
  background: white;
  padding: 22px;
  box-shadow: var(--shadow-dialog);
}
.dialog h2 {
  margin: 0;
  font-size: 18px;
}
.dialog p {
  color: var(--color-text-muted);
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>
