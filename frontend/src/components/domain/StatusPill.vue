<script setup>
import { computed } from "vue";
import { INCIDENT_STATUS } from "@/lib/vocab";
const props = defineProps({ status: String });
const s = computed(() => INCIDENT_STATUS[props.status] || { label: props.status, tone: "neutral" });
</script>
<template><UiPill :tone="s.tone">{{ s.label }}</UiPill></template>
