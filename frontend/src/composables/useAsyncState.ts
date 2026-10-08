import { onBeforeUnmount, onMounted, reactive } from "vue";
import { errorMessage } from "@/utils/format";

export function useAsyncState<T>(loader: () => Promise<T>, pollMs?: number) {
  const state = reactive({
    data: null as T | null,
    loading: true,
    error: "",
  }) as { data: T | null; loading: boolean; error: string };
  let timer: number | undefined;
  let activeRequest: Promise<void> | null = null;

  const load = async (quiet = false) => {
    if (activeRequest) return activeRequest;
    if (!quiet) state.loading = true;
    activeRequest = loader()
      .then((value) => {
        state.data = value;
        state.error = "";
      })
      .catch((reason) => {
        state.error = errorMessage(reason);
      })
      .finally(() => {
        state.loading = false;
        activeRequest = null;
      });
    return activeRequest;
  };

  onMounted(() => {
    void load();
    if (pollMs)
      timer = window.setInterval(() => {
        if (!document.hidden) void load(true);
      }, pollMs);
  });
  onBeforeUnmount(() => {
    if (timer) window.clearInterval(timer);
  });

  return Object.assign(state, { load });
}
