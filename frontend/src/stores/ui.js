import { defineStore } from "pinia";

/** UI chrome shared by every page: toasts and the mobile navigation drawer. */
export const useUiStore = defineStore("ui", {
  state: () => ({ toasts: [], navOpen: false, prefs: loadPrefs() }),
  actions: {
    toast(message, tone = "default") {
      const id = Math.random().toString(36).slice(2);
      this.toasts.push({ id, message, tone });
      setTimeout(() => (this.toasts = this.toasts.filter((t) => t.id !== id)), 3200);
    },
    setPref(key, value) {
      this.prefs[key] = value;
      try { localStorage.setItem("aiops.prefs", JSON.stringify(this.prefs)); } catch { /* private mode */ }
    },
  },
});

function loadPrefs() {
  try { return JSON.parse(localStorage.getItem("aiops.prefs")) || {}; } catch { return {}; }
}
