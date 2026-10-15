<template>
  <div class="page">
    <UiPageHeader title="Connect something to watch"
                  subtitle="AIOps watches what you connect, learns what normal looks like, and investigates on its own when something breaks. Start by connecting one thing — pick whichever you have." />
    <div class="choices">
      <router-link to="/connect/computer" class="choice choice--primary">
        <span class="choice__tag">Most people start here</span>
        <UiAppTile icon="laptop" color="var(--c-chart-4)" :size="48" />
        <b>A computer or server</b>
        <span class="muted">Run one command on it (or let AIOps sign in and do it). You get CPU, memory and disk, and every service on it shows up. On Linux those services are traced automatically — no code change.</span>
        <span class="choice__get">You get: health · services · auto-tracing</span>
        <span class="logos"><UiLogo v-for="[l, a] in [['apple', 'macOS'], ['ubuntu', 'Ubuntu'], ['debian', 'Debian'], ['redhat', 'Red Hat'], ['linux', 'Linux'], ['docker', 'Docker']]" :key="l" :name="l" :size="26" :alt="a" /></span>
        <span class="go">1 command — connect a computer ›</span>
      </router-link>
      <router-link to="/connect/service" class="choice">
        <UiAppTile logo="otel" :size="48" />
        <b>One app, in request-level detail</b>
        <span class="muted">Already have an app you want to see deeply? Turn on OpenTelemetry in it to trace every request, its errors and latency, and the exact hop where one fails.</span>
        <span class="choice__get">You get: requests · errors · traces</span>
        <span class="logos"><UiLogo v-for="l in ['python', 'node', 'java', 'dotnet', 'go', 'ruby', 'php']" :key="l" :name="l" :size="26" :alt="l" /></span>
        <span class="go">3 steps — instrument an app ›</span>
      </router-link>
      <router-link to="/connect/website" class="choice">
        <UiAppTile icon="globe" color="var(--c-chart-2)" :size="48" />
        <b>A website, from the outside</b>
        <span class="muted">Can't install anything? Just give a URL. AIOps calls it every 10 seconds like a browser, learns its normal speed, and opens an incident when it slows down or stops answering.</span>
        <span class="choice__get">You get: uptime · response time</span>
        <span class="go">No install — watch a URL ›</span>
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
.choices { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; align-items: stretch; }
.choice { position: relative; background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 22px; color: var(--c-text); display: flex; flex-direction: column; gap: 8px; border: 2px solid transparent; }
.choice:hover { border-color: var(--c-primary); }
.choice--primary { border-color: var(--c-primary-tint-2); }
.choice__tag { position: absolute; top: -10px; left: 20px; background: var(--c-primary); color: var(--c-on-primary); font-size: var(--fs-xs); font-weight: var(--fw-semibold); padding: 2px 10px; border-radius: var(--radius-pill); }
.choice b { font-size: 19px; }
.choice__get { font-size: var(--fs-sm); color: var(--c-text-2); font-weight: var(--fw-medium); }
.logos { display: flex; gap: 10px; flex-wrap: wrap; }
.go { color: var(--c-primary); font-weight: var(--fw-semibold); margin-top: auto; padding-top: 4px; }
@media (max-width: 760px) { .choices { grid-template-columns: 1fr; } }
</style>
