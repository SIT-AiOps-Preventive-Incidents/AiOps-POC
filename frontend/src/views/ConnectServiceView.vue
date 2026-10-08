<script setup>
import { computed, ref } from "vue";
import { useRoute } from "vue-router";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { slug } from "@/lib/format";
import { useAppStore } from "@/stores/app";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const route = useRoute();
const ui = useUiStore();
const app = useAppStore();
const cat = useCatalogStore();
const step = ref(1);
const svc = ref(route.query.name ? String(route.query.name) : "");
const owner = ref(ui.prefs.lastOwner || "");
const rt = ref("python");
const origin = window.location.origin;
const otlp = computed(() => app.otlpEndpoint);
const status = ref(null);

const RUNTIMES = [
  { value: "python", label: "Python", logo: "python" }, { value: "node", label: "Node.js", logo: "node" },
  { value: "java", label: "Java", logo: "java" }, { value: "dotnet", label: ".NET", logo: "dotnet" },
  { value: "docker", label: "Docker", logo: "docker" }, { value: "test", label: "Just test", logo: "otel" },
];
const hex = (n) => [...crypto.getRandomValues(new Uint8Array(n))].map((b) => b.toString(16).padStart(2, "0")).join("");
const snippet = computed(() => {
  const s = svc.value || "my-service", o = otlp.value;
  const env = `export OTEL_SERVICE_NAME=${s}\nexport OTEL_EXPORTER_OTLP_ENDPOINT=${o}\nexport OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`;
  switch (rt.value) {
    case "python": return `pip install opentelemetry-distro opentelemetry-exporter-otlp\nopentelemetry-bootstrap -a install\n\n${env}\nexport OTEL_LOGS_EXPORTER=otlp\nexport OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true\n\nopentelemetry-instrument python app.py`;
    case "node": return `npm install @opentelemetry/api @opentelemetry/auto-instrumentations-node\n\n${env}\nexport NODE_OPTIONS="--require @opentelemetry/auto-instrumentations-node/register"\n\nnode app.js`;
    case "java": return `curl -LO https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar\n\n${env}\n\njava -javaagent:./opentelemetry-javaagent.jar -jar app.jar`;
    case "dotnet": return `curl -sSfL https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation/releases/latest/download/otel-dotnet-auto-install.sh -O\nsh ./otel-dotnet-auto-install.sh\n. $HOME/.otel-dotnet-auto/instrument.sh\n\n${env}\n\ndotnet run`;
    case "docker": return `# docker-compose.yml: add under your service\n    environment:\n      OTEL_SERVICE_NAME: ${s}\n      OTEL_EXPORTER_OTLP_ENDPOINT: ${o}\n      OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf\n      OTEL_LOGS_EXPORTER: otlp`;
    default: {
      const t = BigInt(Date.now()) * 1000000n;
      const body = { resourceSpans: [{ resource: { attributes: [{ key: "service.name", value: { stringValue: s } }] }, scopeSpans: [{ spans: [{ traceId: hex(16), spanId: hex(8),
        name: "GET /hello", kind: 2, startTimeUnixNano: String(t), endTimeUnixNano: String(t + 42000000n), status: {} }] }] }] };
      return `# sends one test request trace. No app needed.\ncurl -X POST ${o}/v1/traces -H 'Content-Type: application/json' \\\n  -d '${JSON.stringify(body)}'`;
    }
  }
});
const ci = computed(() => `curl -X POST ${origin}/api/v1/deployments -H 'Content-Type: application/json' \\\n  -d '{"service":"${svc.value || "my-service"}","version":"1.4.0","commit":"'$CI_COMMIT_SHORT_SHA'","author":"'$GITLAB_USER_LOGIN'"}'`);

async function next() {
  svc.value = slug(svc.value);
  if (!svc.value) return ui.toast("Enter a service name");
  ui.setPref("lastOwner", owner.value);
  try {
    await cat.addService({ service_name: svc.value, owner: owner.value || "unassigned" });
  } catch (e) {
    if (e.status !== 409) return ui.toast(e.message); // already registered is fine
  }
  step.value = 2;
}
usePolling(async () => {
  if (step.value < 2) return;
  status.value = await api.services.telemetry(svc.value);
  if (status.value.metrics || status.value.traces || status.value.logs) step.value = 3;
}, 4000);
const ok = (b) => (b ? "ok" : "neutral");
</script>
<template>
  <div class="page page--narrow">
    <UiPageHeader title="Connect a service" :back="{ to: '/connect', label: 'Connect' }" subtitle="For request-level detail. Connecting the computer already shows the app as a box; this adds requests, errors and latency." />
    <ol class="steps">
      <li :class="['step', { done: step > 1 }]"><span class="n">1</span><div class="body"><h2>Name your service</h2>
        <template v-if="step === 1">
          <UiField v-model="svc" label="Service name" placeholder="order-api" />
          <UiField v-model="owner" label="Owner team" hint="(approves fixes)" placeholder="team-orders" @enter="next" />
          <UiButton class="mt" @click="next">Continue</UiButton>
        </template>
        <div v-else><b>{{ svc }}</b> <span class="muted">· owner {{ owner || "unassigned" }}</span> <UiButton variant="plain" size="sm" @click="step = 1">Change</UiButton></div></div></li>
      <li :class="['step', { done: step > 2, todo: step < 2 }]"><span class="n">2</span><div class="body"><h2>Turn on OpenTelemetry</h2>
        <template v-if="step >= 2">
          <UiSegmented v-model="rt" :options="RUNTIMES" label="Language" class="seg" />
          <UiCodeBlock :code="snippet" />
          <p class="small muted mt-2">{{ rt === "test" ? "Run this to check the connection before touching your app." : "No code changes. Restart your app with these settings." }}</p>
          <UiDisclosure :card="false" title="Optional: link deployments to problems" class="mt-2">
            <p class="small muted">Add this at the end of your CI pipeline so the AI can tie a problem to the commit behind it.</p><UiCodeBlock :code="ci" /></UiDisclosure>
        </template><p v-else class="small muted">Pick your language after step 1.</p></div></li>
      <li :class="['step', { done: step === 3, todo: step < 2 }]"><span class="n">3</span><div class="body"><h2>Check the data arrives</h2>
        <UiWait v-if="step === 2" :title="`Waiting for the first data from ${svc}…`" subtitle="This updates by itself." />
        <template v-else-if="step === 3">
          <UiWait done :title="`${svc} is sending data`"><span class="row row--wrap mt-2"><UiPill :tone="ok(status?.traces)">traces</UiPill><UiPill :tone="ok(status?.metrics)">metrics</UiPill><UiPill :tone="ok(status?.logs)">logs</UiPill></span></UiWait>
          <div class="row mt"><UiButton :to="`/services/${svc}`">Open {{ svc }}</UiButton><UiButton variant="tint" to="/map">See it on the map</UiButton></div>
        </template><p v-else class="small muted">Starts after step 2.</p></div></li>
    </ol>
  </div>
</template>
<style scoped>
.steps { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 14px; }
.step { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 18px 20px; display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 14px; }
.step.todo { opacity: 0.6; }
.n { width: 28px; height: 28px; border-radius: 50%; background: var(--c-primary); color: #fff; font-weight: 700; font-size: 14px; display: grid; place-items: center; }
.step.done .n { background: var(--c-ok); } .step.todo .n { background: var(--c-fill-2); color: var(--c-text-3); }
.body { min-width: 0; } h2 { font-size: var(--fs-lg); margin: 2px 0 8px; }
.seg { margin-bottom: 12px; }
</style>
