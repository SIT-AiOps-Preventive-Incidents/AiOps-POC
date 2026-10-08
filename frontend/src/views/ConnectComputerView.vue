<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import AppIcon from "@/components/common/AppIcon.vue";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import CodeBlock from "@/components/common/CodeBlock.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
const ui = useUiStore(),
  router = useRouter();
const name = ref(localStorage.getItem("ccName") || "my-mac"),
  os = ref<"mac" | "linux">("mac"),
  found = ref(false),
  serverName = ref(""),
  address = ref(""),
  busy = ref(false);
const clean = computed(
  () =>
    name.value
      .toLowerCase()
      .replace(/\s+/g, "-")
      .replace(/[^a-z0-9._-]/g, "") || "my-mac",
);
const command = computed(
  () =>
    `curl -fsSL ${location.origin}/install/agent.sh | AIOPS_HOST_NAME=${clean.value} sh`,
);
let timer: number | undefined;
async function poll() {
  const hosts = await api.hosts().catch(() => []);
  found.value = hosts.some(
    (h) =>
      h.name === clean.value &&
      (h.status === "healthy" || h.status === "problem"),
  );
  if (found.value && timer) clearInterval(timer);
}
onMounted(() => {
  void poll();
  timer = window.setInterval(() => {
    if (!document.hidden) void poll();
  }, 3000);
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
});
function remember() {
  localStorage.setItem("ccName", clean.value);
  void poll();
}
async function addServer() {
  if (!serverName.value.trim() || !address.value.trim())
    return ui.notify("Enter a name and address");
  busy.value = true;
  try {
    await api.createHost({
      name: serverName.value.trim(),
      address: address.value.trim(),
    });
    ui.notify("Server added");
    router.push(`/infra/${serverName.value.trim()}`);
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Could not add server");
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page narrow">
    <RouterLink class="back" to="/connect">‹ Connect</RouterLink
    ><PageHeader
      title="Connect Infrastructure"
      description="Install the outbound-only agent or register an existing node_exporter."
    /><BasePanel title="1 · Name it"
      ><BaseInput v-model="name" label="Computer name" @input="remember" />
      <div class="segments">
        <button :class="{ on: os === 'mac' }" @click="os = 'mac'">
          <AppIcon name="apple" set="brand" :size="16" />macOS</button
        ><button :class="{ on: os === 'linux' }" @click="os = 'linux'">
          <AppIcon name="linux" set="brand" :size="16" />Linux
        </button>
      </div></BasePanel
    ><BasePanel
      :title="`2 · Paste this in Terminal on the ${os === 'mac' ? 'Mac' : 'server'}`"
      ><CodeBlock :code="command" />
      <p class="muted">
        No sudo required. The agent starts automatically and sends measurements
        outbound.
      </p></BasePanel
    ><BasePanel title="3 · Wait for it to appear"
      ><div :class="['waiting', { found }]">
        <b>{{ found ? `${clean} is connected` : `Waiting for ${clean}…` }}</b
        ><span>{{
          found
            ? "Measurements are arriving."
            : "This updates automatically every three seconds."
        }}</span>
      </div>
      <RouterLink v-if="found" :to="`/infra/${clean}`"
        ><BaseButton>View {{ clean }}</BaseButton></RouterLink
      ></BasePanel
    >
    <details>
      <summary>Advanced: server already running node_exporter</summary>
      <div class="advanced">
        <BaseInput
          v-model="serverName"
          label="Name"
          placeholder="db-01"
        /><BaseInput
          v-model="address"
          label="Address"
          placeholder="10.4.82.30:9100"
        /><BaseButton :disabled="busy" @click="addServer">{{
          busy ? "Adding…" : "Add server"
        }}</BaseButton>
      </div>
    </details>
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
.segments {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
.segments button {
  display: flex;
  align-items: center;
  gap: 7px;
  border: 1px solid var(--color-border-default);
  border-radius: 7px;
  background: white;
  padding: 8px 12px;
}
.segments button.on {
  border-color: var(--color-accent-primary);
  background: var(--color-status-info-bg);
}
.waiting {
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  background: var(--color-surface-subtle);
  padding: 14px;
}
.waiting.found {
  background: var(--color-status-success-bg);
  color: var(--color-status-success-text);
}
.waiting span {
  font-size: 12px;
}
details {
  margin-top: 14px;
  border: 1px solid var(--color-border-default);
  border-radius: 8px;
  background: white;
  padding: 14px;
}
details summary {
  cursor: pointer;
  font-weight: 600;
}
.advanced {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}
</style>
