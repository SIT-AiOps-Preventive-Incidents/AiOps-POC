import { createPinia } from "pinia";
import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import * as ui from "./components/ui";
import "./styles/tokens.css";
import "./styles/base.css";

const app = createApp(App).use(createPinia()).use(router);
// The design-system primitives are used on every page, so they are registered once, globally.
for (const [name, component] of Object.entries(ui)) app.component(name, component);
app.mount("#app");
