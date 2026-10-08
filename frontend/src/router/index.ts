import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: "/",
      name: "overview",
      component: () => import("@/views/OverviewView.vue"),
      meta: { title: "Home" },
    },
    {
      path: "/map",
      name: "map",
      component: () => import("@/views/ServiceMapView.vue"),
      meta: { title: "Service Map" },
    },
    {
      path: "/services",
      name: "services",
      component: () => import("@/views/ServicesView.vue"),
      meta: { title: "Services" },
    },
    {
      path: "/services/:service",
      name: "service-detail",
      component: () => import("@/views/ServiceDetailView.vue"),
      meta: { title: "Services" },
    },
    {
      path: "/infra",
      name: "infra",
      component: () => import("@/views/InfrastructureView.vue"),
      meta: { title: "Computers & Servers" },
    },
    {
      path: "/infra/:name",
      name: "host-detail",
      component: () => import("@/views/HostDetailView.vue"),
      meta: { title: "Computers & Servers" },
    },
    {
      path: "/problems",
      name: "problems",
      component: () => import("@/views/ProblemsView.vue"),
      meta: { title: "Problems" },
    },
    {
      path: "/problems/:id(\\d+)",
      name: "problem-detail",
      component: () => import("@/views/ProblemDetailView.vue"),
      meta: { title: "Problems" },
    },
    {
      path: "/deployments",
      name: "deployments",
      component: () => import("@/views/DeploymentsView.vue"),
      meta: { title: "Deployments" },
    },
    {
      path: "/connect",
      name: "connect",
      component: () => import("@/views/ConnectHubView.vue"),
      meta: { title: "Connect" },
    },
    {
      path: "/connect/service",
      name: "connect-service",
      component: () => import("@/views/ConnectServiceView.vue"),
      meta: { title: "Connect" },
    },
    {
      path: "/connect/computer",
      name: "connect-computer",
      component: () => import("@/views/ConnectComputerView.vue"),
      meta: { title: "Connect" },
    },
    { path: "/connect/app", redirect: "/connect" },
    { path: "/connect/infra", redirect: "/connect" },
    {
      path: "/skills",
      name: "skills",
      component: () => import("@/views/SkillsView.vue"),
      meta: { title: "Skills & Scores" },
    },
    {
      path: "/runbooks",
      name: "runbooks",
      component: () => import("@/views/RunbooksView.vue"),
      meta: { title: "Runbooks" },
    },
    {
      path: "/notifications",
      name: "notifications",
      component: () => import("@/views/NotificationsView.vue"),
      meta: { title: "Notifications" },
    },
    {
      path: "/chaos",
      name: "chaos",
      component: () => import("@/views/ChaosView.vue"),
      meta: { title: "Demo Scenarios" },
    },
    {
      path: "/settings",
      name: "settings",
      component: () => import("@/views/SettingsView.vue"),
      meta: { title: "Settings" },
    },
    {
      path: "/:pathMatch(.*)*",
      component: () => import("@/views/NotFoundView.vue"),
      meta: { title: "Not found" },
    },
  ],
});

router.afterEach((route) => {
  document.title = `${String(route.meta.title || "AiOps One")} · AiOps One`;
});
export default router;
