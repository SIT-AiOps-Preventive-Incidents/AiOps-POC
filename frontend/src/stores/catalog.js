import { defineStore } from "pinia";
import { api } from "@/lib/api";
import { useAppStore } from "./app";

/** What AIOps watches: services (traced, network, discovered) and hosts. */
export const useCatalogStore = defineStore("catalog", {
  state: () => ({ services: [], hosts: [], unregistered: [], loaded: false }),
  getters: {
    applications: (s) => s.services.filter((x) => x.kind === "service"),
    network: (s) => s.services.filter((x) => x.kind === "network"),
    discoveredProcesses: (s) => s.services.filter((x) => x.kind === "process" || x.kind === "external"),
  },
  actions: {
    async loadServices() {
      const [services, unregistered] = await Promise.all([api.services.list(), api.services.discovered().catch(() => [])]);
      this.services = services;
      this.unregistered = unregistered;
      this.loaded = true;
    },
    async loadHosts() {
      this.hosts = await api.hosts.list();
    },
    async addService(body) {
      const s = await api.services.create(body);
      await this.loadServices();
      useAppStore().load().catch(() => {});
      return s;
    },
    async updateService(name, body) {
      const s = await api.services.update(name, body);
      await this.loadServices();
      return s;
    },
    async removeService(name) {
      await api.services.remove(name);
      this.services = this.services.filter((s) => s.service !== name);
    },
    async addHost(body) {
      const h = await api.hosts.create(body);
      await this.loadHosts();
      return h;
    },
    async removeHost(name) {
      await api.hosts.remove(name);
      this.hosts = this.hosts.filter((h) => h.name !== name);
    },
  },
});
