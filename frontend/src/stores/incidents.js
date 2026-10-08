import { defineStore } from "pinia";
import { api } from "@/lib/api";
import { ACTIVE, CLOSED } from "@/lib/vocab";
import { useAppStore } from "./app";

/** Incidents list + a cache of opened incidents, and the owner actions on them. */
export const useIncidentStore = defineStore("incidents", {
  state: () => ({ list: [], byId: {}, loaded: false }),
  getters: {
    needsApproval: (s) => s.list.filter((i) => i.status === "awaiting_approval"),
    inProgress: (s) => s.list.filter((i) => ACTIVE.includes(i.status)),
    recentlyClosed: (s) => s.list.filter((i) => CLOSED.includes(i.status)).slice(0, 30),
  },
  actions: {
    async loadList() {
      this.list = await api.incidents.list();
      this.loaded = true;
    },
    async load(id) {
      this.byId[id] = await api.incidents.get(id);
      return this.byId[id];
    },
    async decide(id, body) {
      // 403 owner_required / 409 wrong state / 422 preflight_failed are surfaced to the caller as ApiError
      this.byId[id] = await api.incidents.decide(id, body);
      useAppStore().load().catch(() => {});
      return this.byId[id];
    },
    async feedback(id, body) {
      const r = await api.incidents.feedback(id, body);
      await this.load(id);
      return r;
    },
    async close(id) {
      this.byId[id] = await api.incidents.close(id);
      useAppStore().load().catch(() => {});
    },
    async reanalyze(id) {
      await api.incidents.reanalyze(id);
      await this.load(id);
    },
  },
});
