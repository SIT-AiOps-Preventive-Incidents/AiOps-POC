import { defineStore } from "pinia";
import { ref } from "vue";

export const useUiStore = defineStore("ui", () => {
  const toast = ref("");
  const sidebarOpen = ref(false);
  let toastTimer: number | undefined;
  function notify(message: string) {
    toast.value = message;
    if (toastTimer) window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => {
      toast.value = "";
    }, 3200);
  }
  return { toast, sidebarOpen, notify };
});
