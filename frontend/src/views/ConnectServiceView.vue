<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import { RouterLink } from "vue-router";
import AppIcon from "@/components/common/AppIcon.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import CodeBlock from "@/components/common/CodeBlock.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import StatusChip from "@/components/common/StatusChip.vue";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
import type { VerifyResponse } from "@/types/api";
const ui = useUiStore(),
  origin = window.location.origin;
const step = ref(1),
  service = ref(""),
  owner = ref(localStorage.getItem("lastOwner") || ""),
  runtime = ref("python"),
  endpoint = ref(origin.replace(/:\d+$/, ":4318")),
  verify = ref<VerifyResponse | null>(null),
  busy = ref(false);
let timer: number | undefined;
void api
  .discover()
  .then((d) => {
    endpoint.value = d.otlp_endpoint || endpoint.value;
  })
  .catch(() => {});
const clean = computed(() =>
  service.value.trim().toLowerCase().replace(/\s+/g, "-"),
);
const snippets: Record<string, () => string> = {
  python: () =>
    `pip install opentelemetry-distro opentelemetry-exporter-otlp\nopentelemetry-bootstrap -a install\n\nexport OTEL_SERVICE_NAME=${clean.value}\nexport OTEL_EXPORTER_OTLP_ENDPOINT=${endpoint.value}\nexport OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf\nexport OTEL_LOGS_EXPORTER=otlp\n\nopentelemetry-instrument python app.py`,
  node: () =>
    `npm install @opentelemetry/api @opentelemetry/auto-instrumentations-node\n\nexport OTEL_SERVICE_NAME=${clean.value}\nexport OTEL_EXPORTER_OTLP_ENDPOINT=${endpoint.value}\nexport OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf\nexport NODE_OPTIONS="--require @opentelemetry/auto-instrumentations-node/register"\n\nnode app.js`,
  java: () =>
    `curl -LO https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar\nexport OTEL_SERVICE_NAME=${clean.value}\nexport OTEL_EXPORTER_OTLP_ENDPOINT=${endpoint.value}\njava -javaagent:./opentelemetry-javaagent.jar -jar app.jar`,
  dotnet: () =>
    `export OTEL_SERVICE_NAME=${clean.value}\nexport OTEL_EXPORTER_OTLP_ENDPOINT=${endpoint.value}\ndotnet run`,
  docker: () =>
    `# docker-compose.yml\nenvironment:\n  OTEL_SERVICE_NAME: ${clean.value}\n  OTEL_EXPORTER_OTLP_ENDPOINT: ${endpoint.value}\n  OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf`,
};
const snippet = computed(() => snippets[runtime.value]?.() || "");
const deploySnippet = computed(
  () =>
    `curl -X POST ${origin}/api/deployments -H 'Content-Type: application/json' -d '{"service":"${clean.value}","version":"1.4.0","commit":"'$CI_COMMIT_SHORT_SHA'"}'`,
);
async function next() {
  if (!clean.value) return ui.notify("Enter a service name");
  busy.value = true;
  try {
    await api.createApp({
      service_name: clean.value,
      owner: owner.value.trim() || "unassigned",
    });
  } catch (e) {
    if (!(e instanceof Error) || !e.message.toLowerCase().includes("already")) {
      ui.notify(e instanceof Error ? e.message : "Could not add service");
      busy.value = false;
      return;
    }
  }
  localStorage.setItem("lastOwner", owner.value);
  step.value = 2;
  busy.value = false;
  timer = window.setInterval(() => {
    if (!document.hidden) void poll();
  }, 4000);
  void poll();
}
async function poll() {
  verify.value = await api.verifyApp(clean.value).catch(() => null);
  if (
    verify.value &&
    (verify.value.metrics || verify.value.logs || verify.value.traces)
  ) {
    step.value = 3;
    if (timer) clearInterval(timer);
  }
}
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
function reset() {
  step.value = 1;
  service.value = "";
  verify.value = null;
}
</script>
<template>
  <div class="page narrow">
    <RouterLink class="back" to="/connect">‹ Connect</RouterLink
    ><PageHeader
      title="Connect App"
      description="Instrument a service with OpenTelemetry and verify data end to end."
    /><BasePanel title="1 · Name your service"
      ><template v-if="step === 1"
        ><BaseInput
          v-model="service"
          label="Service name"
          placeholder="order-api"
        /><BaseInput
          v-model="owner"
          label="Owner team (approves fixes)"
          placeholder="team-orders"
        /><BaseButton :disabled="busy" @click="next"
          >Continue</BaseButton
        ></template
      >
      <div v-else>
        <b>{{ clean }}</b> · owner {{ owner || "unassigned" }}
        <BaseButton variant="ghost" @click="step = 1">Change</BaseButton>
      </div></BasePanel
    ><BasePanel title="2 · Turn on OpenTelemetry"
      ><template v-if="step >= 2"
        ><div class="runtimes">
          <button
            v-for="r in ['python', 'node', 'java', 'dotnet', 'docker']"
            :key="r"
            :class="{ on: runtime === r }"
            @click="runtime = r"
          >
            <AppIcon :name="r" set="brand" :size="16" />{{ r }}
          </button>
        </div>
        <CodeBlock :code="snippet" />
        <p class="muted">
          No source changes are required. Restart the service with these
          settings.
        </p>
        <details>
          <summary>Optional: link deployments to problems</summary>
          <CodeBlock :code="deploySnippet" /></details
      ></template>
      <p v-else class="muted">
        Complete step 1 to generate the correct setup.
      </p></BasePanel
    ><BasePanel title="3 · Check the data arrives"
      ><div v-if="step < 2" class="muted">Starts after step 2.</div>
      <div v-else class="verify" :class="{ done: step === 3 }">
        <b>{{
          step === 3
            ? `${clean} is sending data`
            : `Waiting for the first data from ${clean}…`
        }}</b>
        <div>
          <StatusChip :tone="verify?.traces ? 'success' : 'neutral'"
            >{{ verify?.traces ? "✓ " : "" }}traces</StatusChip
          ><StatusChip :tone="verify?.metrics ? 'success' : 'neutral'"
            >{{ verify?.metrics ? "✓ " : "" }}metrics</StatusChip
          ><StatusChip :tone="verify?.logs ? 'success' : 'neutral'"
            >{{ verify?.logs ? "✓ " : "" }}logs</StatusChip
          >
        </div>
      </div>
      <div v-if="step === 3" class="actions">
        <RouterLink :to="`/services/${clean}`"
          ><BaseButton>Open {{ clean }}</BaseButton></RouterLink
        ><RouterLink to="/map"
          ><BaseButton variant="secondary"
            >See it on the map</BaseButton
          ></RouterLink
        ><BaseButton variant="ghost" @click="reset">Connect another</BaseButton>
      </div></BasePanel
    >
  </div>
</template>
<style scoped>
.narrow {
  max-width: 760px;
}
.back {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--color-accent-primary);
}
.page > :deep(.panel) + :deep(.panel) {
  margin-top: 12px;
}
.page :deep(.input) + :deep(.input) {
  margin-top: 12px;
}
.page :deep(.button) {
  margin-top: 12px;
}
.runtimes {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.runtimes button {
  display: flex;
  align-items: center;
  gap: 5px;
  border: 1px solid var(--color-border-default);
  border-radius: 7px;
  background: white;
  padding: 7px 9px;
  text-transform: capitalize;
}
.runtimes button.on {
  border-color: var(--color-accent-primary);
  background: var(--color-status-info-bg);
}
details {
  margin-top: 10px;
}
.verify {
  display: grid;
  gap: 10px;
  border-radius: 8px;
  background: var(--color-surface-subtle);
  padding: 14px;
}
.verify.done {
  background: var(--color-status-success-bg);
}
.verify > div,
.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
