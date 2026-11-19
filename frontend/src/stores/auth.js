import { defineStore } from "pinia";
import { api } from "@/lib/api";
import { can } from "@/lib/access";

/** The signed-in person: who they are and what their role allows. `loaded` is true once /auth/me has answered. */
export const useAuthStore = defineStore("auth", {
  state: () => ({ me: null, loaded: false }),
  getters: {
    can: (s) => (perm) => can(s.me, perm),
  },
  actions: {
    async load() {
      try { this.me = await api.auth.me(); } catch { this.me = null; }
      this.loaded = true;
      return this.me;
    },
    async login(email, password) {
      this.me = await api.auth.login({ email, password });
      this.loaded = true;
      return this.me;
    },
    async logout() {
      try { await api.auth.logout(); } finally { this.me = null; }
    },
  },
});
