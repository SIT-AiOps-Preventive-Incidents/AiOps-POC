import { createRouter, createWebHashHistory } from "vue-router";
import { nextPath } from "@/lib/access";
import { useAuthStore } from "@/stores/auth";

// Views are lazy-loaded so the first paint only ships the shell + the page you open.
const routes = [
  { path: "/", component: () => import("@/views/HomeView.vue"), meta: { title: "Overview" } },
  { path: "/problems", component: () => import("@/views/ProblemsView.vue"), meta: { title: "Incidents" } },
  { path: "/problems/:id", component: () => import("@/views/ProblemDetailView.vue"), props: true, meta: { title: "Incident" } },
  { path: "/map", component: () => import("@/views/ServiceMapView.vue"), meta: { title: "Service Map" } },
  { path: "/network", component: () => import("@/views/NetworkMapView.vue"), meta: { title: "Fleet" } },
  { path: "/network/map", redirect: "/network" },
  { path: "/network/3d", component: () => import("@/views/Topology3DView.vue"), meta: { title: "Fleet in 3D" } },
  { path: "/network/list", component: () => import("@/views/DiscoveredNetworkView.vue"), meta: { title: "Fleet list" } },
  { path: "/network/yours", redirect: "/network/list" },
  { path: "/cloud", component: () => import("@/views/CloudView.vue"), meta: { title: "Cloud accounts" } },
  { path: "/connect/cloud", redirect: { path: "/cloud", query: { add: "1" } } },
  { path: "/insights", component: () => import("@/views/InsightsView.vue"), meta: { title: "Insights" } },
  { path: "/services", component: () => import("@/views/ServicesView.vue"), meta: { title: "Services" } },
  { path: "/services/:name", component: () => import("@/views/ServiceDetailView.vue"), props: true, meta: { title: "Service" } },
  { path: "/computers", component: () => import("@/views/HostsView.vue"), meta: { title: "Hosts" } },
  { path: "/computers/:name", component: () => import("@/views/HostDetailView.vue"), props: true, meta: { title: "Host" } },
  { path: "/connect", component: () => import("@/views/ConnectView.vue"), meta: { title: "Connect", perm: "fleet.connect" } },
  { path: "/connect/computer", component: () => import("@/views/ConnectComputerView.vue"), meta: { title: "Connect a computer", perm: "fleet.connect" } },
  { path: "/connect/service", component: () => import("@/views/ConnectServiceView.vue"), meta: { title: "Connect a service", perm: "fleet.connect" } },
  { path: "/connect/website", component: () => import("@/views/ConnectWebsiteView.vue"), meta: { title: "Watch a website", perm: "fleet.connect" } },
  { path: "/skills", component: () => import("@/views/SkillsView.vue"), meta: { title: "Skills" } },
  { path: "/playbooks", component: () => import("@/views/PlaybooksView.vue"), meta: { title: "Playbooks" } },
  { path: "/runbooks", component: () => import("@/views/RunbooksView.vue"), meta: { title: "Runbooks" } },
  { path: "/notifications", component: () => import("@/views/NotificationsView.vue"), meta: { title: "Notifications" } },
  { path: "/deployments", component: () => import("@/views/DeploymentsView.vue"), meta: { title: "Deployments" } },
  { path: "/scenarios", component: () => import("@/views/ScenariosView.vue"), meta: { title: "Demo Scenarios", perm: "demo.run" } },
  { path: "/pricing", component: () => import("@/views/PricingView.vue"), meta: { title: "Pricing" } },
  { path: "/design", component: () => import("@/views/DesignSystemView.vue"), meta: { title: "Design System" } },
  { path: "/settings", component: () => import("@/views/SettingsView.vue"), meta: { title: "Settings", perm: "settings.edit" } },
  { path: "/access", component: () => import("@/views/AccessView.vue"), meta: { title: "Access", perm: "admin" } },
  { path: "/login", component: () => import("@/views/LoginView.vue"), meta: { title: "Sign in", public: true, bare: true } },
  // old links (v2 UI, Teams cards)
  { path: "/infra", redirect: "/computers" },
  { path: "/infra/:name", redirect: (to) => `/computers/${to.params.name}` },
  { path: "/chaos", redirect: "/scenarios" },
  { path: "/:pathMatch(.*)*", component: () => import("@/views/NotFoundView.vue") },
];

const router = createRouter({ history: createWebHashHistory(), routes, scrollBehavior: () => ({ top: 0 }) });
// Every page needs a session; a page can also need a permission (meta.perm). The server checks every call anyway.
router.beforeEach(async (to) => {
  const auth = useAuthStore();
  if (!auth.loaded) await auth.load();
  if (to.meta.public) return auth.me && to.path === "/login" ? nextPath(to.query.next) : true;
  if (!auth.me) return { path: "/login", query: to.fullPath === "/" ? {} : { next: to.fullPath } };
  if (to.meta.perm && !auth.can(to.meta.perm)) return "/";
  return true;
});
// a call answered 401: the session ended (expired, signed out elsewhere, blocked) - back to sign-in, then back here
window.addEventListener("radarops:signed-out", () => {
  const auth = useAuthStore();
  const cur = router.currentRoute.value;
  if (cur.meta.public) return;
  auth.me = null;
  router.replace({ path: "/login", query: { next: cur.fullPath } });
});
router.afterEach((to) => { document.title = to.meta.title ? `${to.meta.title} · RadarOps` : "RadarOps"; });
export default router;
