import { createRouter, createWebHashHistory } from "vue-router";

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
  { path: "/services", component: () => import("@/views/ServicesView.vue"), meta: { title: "Services" } },
  { path: "/services/:name", component: () => import("@/views/ServiceDetailView.vue"), props: true, meta: { title: "Service" } },
  { path: "/computers", component: () => import("@/views/HostsView.vue"), meta: { title: "Hosts" } },
  { path: "/computers/:name", component: () => import("@/views/HostDetailView.vue"), props: true, meta: { title: "Host" } },
  { path: "/connect", component: () => import("@/views/ConnectView.vue"), meta: { title: "Connect" } },
  { path: "/connect/computer", component: () => import("@/views/ConnectComputerView.vue"), meta: { title: "Connect a computer" } },
  { path: "/connect/service", component: () => import("@/views/ConnectServiceView.vue"), meta: { title: "Connect a service" } },
  { path: "/connect/website", component: () => import("@/views/ConnectWebsiteView.vue"), meta: { title: "Watch a website" } },
  { path: "/skills", component: () => import("@/views/SkillsView.vue"), meta: { title: "Skills" } },
  { path: "/runbooks", component: () => import("@/views/RunbooksView.vue"), meta: { title: "Runbooks" } },
  { path: "/notifications", component: () => import("@/views/NotificationsView.vue"), meta: { title: "Notifications" } },
  { path: "/deployments", component: () => import("@/views/DeploymentsView.vue"), meta: { title: "Deployments" } },
  { path: "/scenarios", component: () => import("@/views/ScenariosView.vue"), meta: { title: "Demo Scenarios" } },
  { path: "/pricing", component: () => import("@/views/PricingView.vue"), meta: { title: "Pricing" } },
  { path: "/design", component: () => import("@/views/DesignSystemView.vue"), meta: { title: "Design System" } },
  { path: "/settings", component: () => import("@/views/SettingsView.vue"), meta: { title: "Settings" } },
  // old links (v2 UI, Teams cards)
  { path: "/infra", redirect: "/computers" },
  { path: "/infra/:name", redirect: (to) => `/computers/${to.params.name}` },
  { path: "/chaos", redirect: "/scenarios" },
  { path: "/:pathMatch(.*)*", component: () => import("@/views/NotFoundView.vue") },
];

const router = createRouter({ history: createWebHashHistory(), routes, scrollBehavior: () => ({ top: 0 }) });
router.afterEach((to) => { document.title = `${to.meta.title || "AIOps"} · AIOps One`; });
export default router;
