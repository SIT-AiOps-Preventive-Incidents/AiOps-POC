<template>
  <div class="page">
    <UiPageHeader eyebrow="Setup" title="Connect something to watch"
                  subtitle="SIT-AIOPS watches what you connect, learns what normal looks like, and investigates on its own when something breaks. Start by connecting one thing — pick whichever you have." />
    <div class="choices">
      <router-link to="/connect/computer" class="choice choice--primary">
        <span class="choice__tag">Most people start here</span>
        <span class="gt"><UiGlyph name="laptop" :size="34" /></span>
        <b>A computer or server</b>
        <span class="muted">Run one command on it (or let SIT-AIOPS sign in and do it). You get CPU, memory and disk, and every service on it shows up. On Linux those services are traced automatically — no code change.</span>
        <span class="choice__get">You get: health · services · auto-tracing</span>
        <span class="logos"><UiLogo v-for="[l, a] in [['apple', 'macOS'], ['ubuntu', 'Ubuntu'], ['debian', 'Debian'], ['redhat', 'Red Hat'], ['linux', 'Linux'], ['docker', 'Docker']]" :key="l" :name="l" :size="26" :alt="a" /></span>
        <span class="go">1 command — connect a computer ›</span>
      </router-link>
      <router-link to="/connect/service" class="choice">
        <span class="gt"><UiGlyph name="pulse" :size="34" /></span>
        <b>One app, in request-level detail</b>
        <span class="muted">Already have an app you want to see deeply? Turn on OpenTelemetry in it to trace every request, its errors and latency, and the exact hop where one fails.</span>
        <span class="choice__get">You get: requests · errors · traces</span>
        <span class="logos"><UiLogo v-for="l in ['python', 'node', 'java', 'dotnet', 'go', 'ruby', 'php']" :key="l" :name="l" :size="26" :alt="l" /></span>
        <span class="go">3 steps — instrument an app ›</span>
      </router-link>
      <router-link to="/cloud?add=1" class="choice">
        <span class="gt"><UiGlyph name="cloud" :size="34" /></span>
        <b>A cloud account</b>
        <span class="muted">Rent your servers? Give SIT-AIOPS a read-only credential and every VM in the account appears on the Fleet, with what the cloud and our agent see together. Proxmox (GIST Starships Cloud), OpenStack, VMware Cloud Director, CloudStack, AWS, Azure, Google Cloud.</span>
        <span class="choice__get">You get: every VM · power state · addresses · changes</span>
        <span class="go">Read-only — connect a cloud ›</span>
      </router-link>
      <router-link to="/connect/website" class="choice">
        <span class="gt"><UiGlyph name="globe" :size="34" /></span>
        <b>A website, from the outside</b>
        <span class="muted">Can't install anything? Just give a URL. SIT-AIOPS calls it every 10 seconds like a browser, learns its normal speed, and opens an incident when it slows down or stops answering.</span>
        <span class="choice__get">You get: uptime · response time</span>
        <span class="go">No install — watch a URL ›</span>
      </router-link>
    </div>
    <div class="section-label">Good to know</div>
    <UiList plain>
      <UiListRow title="Outbound only" subtitle="Your machines send data to SIT-AIOPS. Nothing needs to be opened on them." />
      <UiListRow title="Network" :subtitle="`They must reach this server on ports 8080 and 4318 (KMUTT network or VPN).`" />
      <UiListRow title="Safety" subtitle="SIT-AIOPS never runs anything on a connected computer. Automatic fixes are only for registered services and always need the owner's approval." />
    </UiList>
  </div>
</template>
<style scoped>
.choices { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; align-items: stretch; }
.choice { position: relative; background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 26px; color: var(--c-text); display: flex; flex-direction: column; gap: 10px; border: 1px solid transparent; }
.choice:hover { border-color: color-mix(in srgb, var(--c-primary) 50%, transparent); }
.choice--primary { border-color: var(--c-primary-tint-2); }
.choice__tag { position: absolute; top: -10px; left: 20px; background: var(--c-primary); color: var(--c-on-primary); font-size: var(--fs-xs); font-weight: var(--fw-semibold); padding: 2px 10px; border-radius: var(--radius-pill); }
.gt { width: 56px; height: 56px; border-radius: 16px; display: grid; place-items: center; background: var(--c-fill); box-shadow: 0 0 0 1px var(--c-border); }
.choice b { font-size: 22px; font-weight: var(--fw-semibold); letter-spacing: -0.02em; }
.choice__get { font-size: var(--fs-sm); color: var(--c-text-2); font-weight: var(--fw-medium); }
.logos { display: flex; gap: 10px; flex-wrap: wrap; }
.go { color: var(--c-primary); font-weight: var(--fw-semibold); margin-top: auto; padding-top: 4px; }
@media (max-width: 760px) { .choices { grid-template-columns: 1fr; } }
</style>
