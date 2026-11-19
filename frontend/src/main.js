import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import { applyTheme } from "./stores/ui";
import { useAuthStore } from "./stores/auth";
import * as ui from "./components/ui";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-sans-thai/400.css";
import "@fontsource/ibm-plex-sans-thai/500.css";
import "@fontsource/ibm-plex-sans-thai/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./styles/tokens.css";
import "./styles/base.css";

// After a redeploy the hashed chunks of the old build are gone. A tab opened before it would load a page's JS from
// cache but miss its CSS (an unstyled page). Vite reports that as vite:preloadError: reload once to get the new build.
window.addEventListener("vite:preloadError", (e) => {
  e.preventDefault();
  if (sessionStorage.getItem("aiops.reloaded") !== "1") { sessionStorage.setItem("aiops.reloaded", "1"); location.reload(); }
});
window.addEventListener("load", () => setTimeout(() => sessionStorage.removeItem("aiops.reloaded"), 10000));
const app = createApp(App).use(createPinia()).use(router);
// The design-system primitives are used on every page, so they are registered once, globally.
for (const [name, component] of Object.entries(ui)) app.component(name, component);
// v-can="'fleet.connect'": an action the signed-in role may not take is not shown (the server refuses it anyway)
const applyCan = (el, b) => { el.style.display = useAuthStore().can(b.value) ? "" : "none"; };
app.directive("can", { mounted: applyCan, updated: applyCan });
app.mount("#app");

// "Auto" theme: keep the browser chrome colour in step when the OS switches light/dark (dark is the default)
const savedTheme = () => { try { return (JSON.parse(localStorage.getItem("aiops.prefs")) || {}).theme || "dark"; } catch { return "dark"; } };
applyTheme(savedTheme());
window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => applyTheme(savedTheme()));
