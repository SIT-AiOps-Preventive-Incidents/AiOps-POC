import { onBeforeUnmount, onMounted } from "vue";

/**
 * Run `fn` now and every `intervalMs` while the component is mounted and the tab is visible.
 * Errors are swallowed after the first call so a flaky network does not spam the user.
 */
export function usePolling(fn, intervalMs) {
  let timer = null;
  let first = true;
  const tick = async () => {
    if (document.hidden && !first) return;
    try {
      await fn();
    } catch (e) {
      if (first) throw e;
    } finally {
      first = false;
    }
  };
  onMounted(() => {
    tick();
    timer = setInterval(tick, intervalMs);
  });
  onBeforeUnmount(() => clearInterval(timer));
  return { refresh: tick };
}
