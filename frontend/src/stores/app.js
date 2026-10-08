import { defineStore } from "pinia";
import { api } from "@/lib/api";

/**
 * Global platform state: the overview payload (services, hosts, open problems, KPIs, AI + detector status).
 * Read by the sidebar badge, the top bar chips and the home page, so it is fetched once and shared.
 */
export const useAppStore = defineStore("app", {
  state: () => ({ overview: null, loading: false, error: null, lastLoaded: 0 }),
  getters: {
    services: (s) => s.overview?.services ?? [],
    discovered: (s) => s.overview?.discovered ?? [],
    hosts: (s) => s.overview?.hosts ?? [],
    openProblems: (s) => s.overview?.open_problems ?? [],
    awaiting: (s) => (s.overview?.open_problems ?? []).filter((p) => p.status === "awaiting_approval"),
    kpi: (s) => s.overview?.kpi ?? {},
    llm: (s) => s.overview?.llm ?? { up: false, models: [] },
    detectorLive: (s) => !!s.overview?.detector?.ts && Date.now() / 1000 - s.overview.detector.ts < 60,
    grafanaUrl: (s) => s.overview?.grafana_url ?? "#",
    otlpEndpoint: (s) => s.overview?.otlp_endpoint ?? `${location.protocol}//${location.hostname}:4318`,
  },
  actions: {
    async load() {
      this.loading = true;
      try {
        this.overview = await api.overview();
        this.error = null;
        this.lastLoaded = Date.now();
      } catch (e) {
        this.error = e.message;
        throw e;
      } finally {
        this.loading = false;
      }
    },
  },
});
