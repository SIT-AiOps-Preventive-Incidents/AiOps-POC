<script setup>
// Official technology logos (Devicon MIT / Simple Icons CC0) in /public/icons/b.
defineProps({ name: { type: String, required: true }, size: { type: Number, default: 20 }, alt: { type: String, default: "" } });
</script>
<template>
  <img class="ui-logo" :src="`/icons/b/${name}.svg`" :width="size" :height="size" :alt="alt" loading="lazy">
</template>
<style scoped>
.ui-logo { display: inline-block; flex: none; object-fit: contain; vertical-align: middle; }
</style>
