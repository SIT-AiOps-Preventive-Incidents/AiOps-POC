<script setup>
import { ref, watch } from "vue";
import { useIncidentStore } from "@/stores/incidents";
import { useUiStore } from "@/stores/ui";
const props = defineProps({ incident: { type: Object, required: true } });
const store = useIncidentStore();
const ui = useUiStore();
const score = ref(props.incident.score || 0);
const correct = ref(props.incident.rca_correct !== false);
const comment = ref(props.incident.feedback || "");
const busy = ref(false);
watch(() => props.incident.id, () => { score.value = props.incident.score || 0; comment.value = props.incident.feedback || ""; });
async function send() {
  if (!score.value) return ui.toast("Tap a star first");
  busy.value = true;
  try {
    const r = await store.feedback(props.incident.id, { score: score.value, rca_correct: correct.value, comment: comment.value });
    ui.toast(r.message === "feedback saved" ? "Thanks, feedback saved" : r.message);
  } catch (e) { ui.toast(e.message); } finally { busy.value = false; }
}
</script>
<template>
  <UiCard title="Rate this analysis">
    <UiStars v-model="score" />
    <div class="line"><span>Root cause was correct</span><UiSwitch v-model="correct" label="Root cause was correct" /></div>
    <UiField v-model="comment" label="What should the AI learn?" multiline />
    <UiButton variant="tint" class="mt-2" :loading="busy" @click="send">Send feedback</UiButton>
    <p class="small dim mt-2">4-5 stars on a resolved problem saves it as a runbook. Low scores teach the AI for next time.</p>
  </UiCard>
</template>
<style scoped>
.line { display: flex; align-items: center; justify-content: space-between; padding: 12px 0 0; margin-top: 10px; border-top: 0.5px solid var(--c-separator); }
</style>
