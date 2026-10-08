import { useUiStore } from "@/stores/ui";

/** Copy text; when the clipboard API is unavailable (plain http on another host), select it for Cmd+C. */
export function useClipboard() {
  const ui = useUiStore();
  async function copy(text, el) {
    try {
      await navigator.clipboard.writeText(text);
      ui.toast("Copied");
    } catch {
      if (el) {
        const r = document.createRange();
        r.selectNodeContents(el);
        getSelection().removeAllRanges();
        getSelection().addRange(r);
      }
      ui.toast("Selected. Press Cmd+C to copy");
    }
  }
  return { copy };
}
