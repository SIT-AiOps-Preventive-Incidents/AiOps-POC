<script setup lang="ts">
import { RouterLink } from "vue-router";
import BaseButton from "@/components/common/BaseButton.vue";
import EmptyState from "@/components/common/EmptyState.vue";
</script>
<template>
  <div class="page">
    <EmptyState
      title="Page not found"
      message="The page you requested does not exist."
      ><RouterLink to="/"
        ><BaseButton>Back to overview</BaseButton></RouterLink
      ></EmptyState
    >
  </div>
</template>
