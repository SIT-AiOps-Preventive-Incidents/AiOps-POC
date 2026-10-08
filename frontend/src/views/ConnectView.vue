<template>
  <div class="page">
    <UiPageHeader title="Connect" subtitle="What do you want AIOps to watch?" />
    <div class="choices">
      <router-link to="/connect/computer" class="choice">
        <UiAppTile icon="laptop" color="var(--c-chart-4)" :size="48" />
        <b>A computer or server</b>
        <span class="muted">Paste one command. You get CPU, memory and disk, and every service running on it appears on the service map. On Linux those services are also traced automatically with eBPF - no code change.</span>
        <span class="logos"><UiLogo v-for="[l, a] in [['apple', 'macOS'], ['ubuntu', 'Ubuntu'], ['debian', 'Debian'], ['redhat', 'Red Hat'], ['linux', 'Linux'], ['docker', 'Docker']]" :key="l" :name="l" :size="26" :alt="a" /></span>
        <span class="go">Recommended · 1 command ›</span>
      </router-link>
      <router-link to="/connect/service" class="choice">
        <UiAppTile logo="otel" :size="48" />
        <b>Request-level detail for an app</b>
        <span class="muted">Turn on OpenTelemetry in one app to see its requests, errors, latency and the exact hop where a request fails.</span>
        <span class="logos"><UiLogo v-for="l in ['python', 'node', 'java', 'dotnet', 'go', 'ruby', 'php']" :key="l" :name="l" :size="26" :alt="l" /></span>
        <span class="go">3 steps ›</span>
      </router-link>
    </div>
    <div class="section-label">Good to know</div>
    <UiList plain>
      <UiListRow title="Outbound only" subtitle="Your machines send data to AIOps. Nothing needs to be opened on them." />
      <UiListRow title="Network" :subtitle="`They must reach this server on ports 8080 and 4318 (KMUTT network or VPN).`" />
      <UiListRow title="Safety" subtitle="AIOps never runs anything on a connected computer. Automatic fixes are only for registered services and always need the owner's approval." />
    </UiList>
  </div>
</template>
<style scoped>
.choices { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.choice { background: var(--c-surface); border-radius: 18px; box-shadow: var(--shadow-1); padding: 22px; color: var(--c-text); display: flex; flex-direction: column; gap: 8px; border: 2px solid transparent; }
.choice:hover { border-color: var(--c-primary); }
.choice b { font-size: 19px; }
.logos { display: flex; gap: 10px; }
.go { color: var(--c-primary); font-weight: var(--fw-semibold); margin-top: auto; }
@media (max-width: 760px) { .choices { grid-template-columns: 1fr; } }
</style>
