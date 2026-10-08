import { createRouter, createWebHashHistory } from "vue-router";

// Views are lazy-loaded so the first paint only ships the shell + the page you open.
const routes = [
  { path: "/", component: () => import("@/views/HomeView.vue"), meta: { title: "Home" } },
  { path: "/problems", component: () => import("@/views/ProblemsView.vue"), meta: { title: "Problems" } },
  { path: "/problems/:id", component: () => import("@/views/ProblemDetailView.vue"), props: true, meta: { title: "Problem" } },
  { path: "/map", component: () => import("@/views/ServiceMapView.vue"), meta: { title: "Service Map" } },
  { path: "/services", component: () => import("@/views/ServicesView.vue"), meta: { title: "Services" } },
  { path: "/services/:name", component: () => import("@/views/ServiceDetailView.vue"), props: true, meta: { title: "Service" } },
  { path: "/computers", component: () => import("@/views/HostsView.vue"), meta: { title: "Computers" } },
  { path: "/computers/:name", component: () => import("@/views/HostDetailView.vue"), props: true, meta: { title: "Computer" } },
  { path: "/connect", component: () => import("@/views/ConnectView.vue"), meta: { title: "Connect" } },
  { path: "/connect/computer", component: () => import("@/views/ConnectComputerView.vue"), meta: { title: "Connect a computer" } },
  { path: "/connect/service", component: () => import("@/views/ConnectServiceView.vue"), meta: { title: "Connect a service" } },
  { path: "/skills", component: () => import("@/views/SkillsView.vue"), meta: { title: "Skills" } },
  { path: "/runbooks", component: () => import("@/views/RunbooksView.vue"), meta: { title: "Runbooks" } },
  { path: "/notifications", component: () => import("@/views/NotificationsView.vue"), meta: { title: "Notifications" } },
  { path: "/deployments", component: () => import("@/views/DeploymentsView.vue"), meta: { title: "Deployments" } },
  { path: "/scenarios", component: () => import("@/views/ScenariosView.vue"), meta: { title: "Demo Scenarios" } },
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
