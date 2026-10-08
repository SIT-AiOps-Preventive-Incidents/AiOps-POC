import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { api } from "@/services/api";
import type { OverviewResponse } from "@/types/api";

export const useSystemStore = defineStore("system", () => {
  const overview = ref<OverviewResponse | null>(null);
  const error = ref("");
  let request: Promise<void> | null = null;
  const openProblems = computed(() => overview.value?.kpi.open ?? 0);
  async function refresh() {
    if (request) return request;
    request = api
      .overview()
      .then((value) => {
        overview.value = value;
        error.value = "";
      })
      .catch((reason) => {
        error.value =
          reason instanceof Error ? reason.message : "Status unavailable";
      })
      .finally(() => {
        request = null;
      });
    return request;
  }
  return { overview, error, openProblems, refresh };
});
