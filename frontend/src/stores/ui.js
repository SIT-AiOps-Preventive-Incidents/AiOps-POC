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
    /** "auto" follows the OS; "light" / "dark" force it. Applied to <html data-theme> (index.html does the first paint). */
    setTheme(mode) {
      this.setPref("theme", mode);
      applyTheme(mode);
    },
    setPref(key, value) {
      this.prefs[key] = value;
      try { localStorage.setItem("aiops.prefs", JSON.stringify(this.prefs)); } catch { /* private mode */ }
    },
  },
});

export const THEMES = ["auto", "light", "dark"];

export function applyTheme(mode) {
  const root = document.documentElement;
  if (mode === "light" || mode === "dark") root.dataset.theme = mode;
  else delete root.dataset.theme;
  const dark = mode === "dark" || (mode !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", dark ? "#000000" : "#f2f2f7");
}

function loadPrefs() {
  try { return JSON.parse(localStorage.getItem("aiops.prefs")) || {}; } catch { return {}; }
}
