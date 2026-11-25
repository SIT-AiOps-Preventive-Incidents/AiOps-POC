import { inject, onBeforeUnmount, onMounted } from "vue";
import { useRoute } from "vue-router";

export const pageFactsKey = Symbol("pageFacts");

// Read the active view's counters and states only when a summary is requested.
export function usePageFacts(read) {
  const active = inject(pageFactsKey);
  const path = useRoute().fullPath;
  const source = { path, read };
  onMounted(() => { active.value = source; });
  onBeforeUnmount(() => { if (active.value === source) active.value = null; });
}
