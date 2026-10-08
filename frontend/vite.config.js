import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

// `npm run dev` proxies the API to the VM so the UI can be developed locally.
export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  server: {
    proxy: {
      "/api": process.env.AIOPS_API || "http://cp26pt1.sit.kmutt.ac.th:8080",
      "/install": process.env.AIOPS_API || "http://cp26pt1.sit.kmutt.ac.th:8080",
    },
  },
});
