<script setup lang="ts">
import { RouterLink } from "vue-router";
import AppIcon from "@/components/common/AppIcon.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import PageHeader from "@/components/common/PageHeader.vue";
const host = window.location.hostname;
</script>
<template>
  <div class="page">
    <PageHeader
      title="Connect"
      description="What do you want AIOps to watch?"
    />
    <div class="choices">
      <RouterLink to="/connect/service"
        ><AppIcon name="services" :size="34" />
        <h2>A service</h2>
        <p>
          Your web app or API. Add OpenTelemetry settings and its traces,
          metrics, and logs start flowing.
        </p>
        <div class="logos">
          <AppIcon
            v-for="logo in [
              'python',
              'node',
              'java',
              'dotnet',
              'docker',
              'otel',
            ]"
            :key="logo"
            :name="logo"
            set="brand"
          />
        </div>
        <b>3 steps ›</b></RouterLink
      ><RouterLink to="/connect/computer"
        ><AppIcon name="computers-servers" :size="34" />
        <h2>A computer or server</h2>
        <p>
          A Mac, Linux server, or VM. One command reports CPU, memory, disk, and
          busiest processes.
        </p>
        <div class="logos">
          <AppIcon name="apple" set="brand" /><AppIcon
            name="linux"
            set="brand"
          />
        </div>
        <b>1 command ›</b></RouterLink
      >
    </div>
    <BasePanel title="Good to know"
      ><dl>
        <dt>Outbound only</dt>
        <dd>
          Your machines send data to AIOps. Nothing needs to be opened on them.
        </dd>
        <dt>Network</dt>
        <dd>They must reach {{ host }} on ports 8080 and 4318.</dd>
        <dt>Safety</dt>
        <dd>
          AIOps never runs commands on connected computers. Service fixes
          require owner approval.
        </dd>
      </dl></BasePanel
    >
  </div>
</template>
<style scoped>
.choices {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.choices > a {
  display: flex;
  min-height: 260px;
  flex-direction: column;
  align-items: flex-start;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: white;
  padding: 24px;
}
.choices > a:hover {
  border-color: var(--color-accent-primary);
}
.choices h2 {
  margin: 18px 0 5px;
}
.choices p {
  color: var(--color-text-muted);
}
.choices > a > b {
  margin-top: auto;
  color: var(--color-accent-primary);
}
.logos {
  display: flex;
  gap: 10px;
  margin: 10px 0;
}
dl {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 10px;
}
dt {
  font-weight: 600;
}
dd {
  margin: 0;
  color: var(--color-text-muted);
}
@media (max-width: 680px) {
  .choices {
    grid-template-columns: 1fr;
  }
}
</style>
