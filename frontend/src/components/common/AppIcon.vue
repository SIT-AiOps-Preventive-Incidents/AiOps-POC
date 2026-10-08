<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    name: string;
    size?: number;
    alt?: string;
    set?: "vm" | "fluent" | "brand";
  }>(),
  { size: 24, alt: "", set: "vm" },
);
const src = computed(
  () =>
    `${import.meta.env.BASE_URL}icons/${props.set === "vm" ? `vm/${props.name}` : props.set === "brand" ? `b/${props.name}` : `f/${props.name}_regular`}.svg`,
);
</script>

<template>
  <img class="app-icon" :src="src" :width="size" :height="size" :alt="alt" />
</template>

<style scoped>
.app-icon {
  display: block;
  flex: none;
  object-fit: contain;
}
</style>
