<script setup>
import { computed } from "vue";
import HostRow from "@/components/domain/HostRow.vue";
import ProblemRow from "@/components/domain/ProblemRow.vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { ago, dur } from "@/lib/format";
import { useAppStore } from "@/stores/app";

const app = useAppStore();
const others = computed(() => app.openProblems.filter((p) => p.status !== "awaiting_approval"));
const hero = computed(() => {
  const n = app.awaiting.length, m = others.value.length;
  if (n) return { tone: "ai", icon: "wand", title: `${n} fix${n > 1 ? "es are" : " is"} waiting for your approval` };
  if (m) return { tone: "bad", icon: "warning", title: `${m} problem${m > 1 ? "s are" : " is"} being investigated` };
  return { tone: "ok", icon: "checkmark", title: "Everything is running normally" };
});
const QUICK = [
  { to: "/connect/computer", icon: "laptop", color: "var(--c-chart-4)", title: "Connect a computer", sub: "One command; its services appear on the map" },
  { to: "/connect/service", icon: "cube", color: "var(--c-primary)", title: "Connect a service", sub: "Turn on OpenTelemetry for request-level detail" },
  { to: "/map", icon: "flowchart", color: "var(--c-chart-5)", title: "Send a test request", sub: "Watch one request travel every hop" },
  { to: "/scenarios", icon: "flash", color: "var(--c-warn)", title: "Try a demo problem", sub: "Break something and watch the AI fix it" },
];
</script>
<template>
  <div class="page">
    <UiPageHeader title="Home" />
    <div v-if="app.overview" class="stack">
      <section :class="['hero', hero.tone]">
        <span class="hero__ic"><UiIcon :name="hero.icon" filled :size="30" /></span>
        <div class="hero__t"><h2>{{ hero.title }}</h2>
          <p class="muted">{{ app.services.length }} services, {{ app.discovered.length }} discovered processes and {{ app.hosts.length }} computers are monitored. Last check {{ ago(app.overview.detector?.ts) }}.</p></div>
        <UiButton v-if="app.openProblems.length" to="/problems">Review</UiButton>
        <UiButton v-else variant="tint" to="/connect">Connect more</UiButton>
      </section>
      <div class="grid grid--4">
        <UiTile label="Open problems" :value="app.kpi.open ?? 0" :hint="`${app.kpi.total ?? 0} in total`" :tone="app.kpi.open ? 'bad' : ''" />
        <UiTile label="Waiting for approval" :value="app.kpi.awaiting_approval ?? 0" hint="fixes already dry-run" />
        <UiTile label="Time to detect" :value="dur(app.kpi.mttd_s)" hint="average" />
        <UiTile label="Time to fix" :value="dur(app.kpi.mttr_s)" hint="detected to verified" />
      </div>
    </div>
    <template v-if="app.openProblems.length">
      <h2 class="section-title">Open problems <router-link to="/problems">See all</router-link></h2>
      <UiList><ProblemRow v-for="p in app.openProblems" :key="p.id" :incident="p" /></UiList>
    </template>
    <div class="grid grid--2">
      <div>
        <h2 class="section-title">Services <router-link to="/services">See all</router-link></h2>
        <UiList><ServiceRow v-for="s in app.services" :key="s.service" :service="s" /></UiList>
        <template v-if="app.discovered.length">
          <h2 class="section-title">Found on your computers</h2>
          <UiList><ServiceRow v-for="s in app.discovered.slice(0, 6)" :key="s.service" :service="s" /></UiList>
        </template>
      </div>
      <div>
        <h2 class="section-title">Computers & servers <router-link to="/computers">See all</router-link></h2>
        <UiList><HostRow v-for="h in app.hosts" :key="h.name" :host="h" /></UiList>
        <h2 class="section-title">Quick actions</h2>
        <UiList><UiListRow v-for="q in QUICK" :key="q.to" :to="q.to" :title="q.title" :subtitle="q.sub">
          <template #leading><UiAppTile :icon="q.icon" :color="q.color" /></template></UiListRow></UiList>
      </div>
    </div>
  </div>
</template>
<style scoped>
.hero { display: flex; align-items: center; gap: 16px; padding: 20px 22px; border-radius: var(--radius-lg); box-shadow: var(--shadow-1); background: var(--c-surface); }
.hero__ic { width: 52px; height: 52px; border-radius: 14px; display: grid; place-items: center; color: #fff; flex: none; }
.hero.ok .hero__ic { background: var(--c-ok); } .hero.bad .hero__ic { background: var(--c-bad); } .hero.ai .hero__ic { background: var(--c-ai); }
.hero__t { flex: 1; min-width: 0; } .hero h2 { font-size: 22px; }
</style>
