<script setup>
// Living style guide: renders the real tokens and components, so the documentation cannot drift from the code.
import { onMounted, ref } from "vue";
const COLORS = [
  ["Neutrals", ["--c-bg", "--c-surface", "--c-fill", "--c-fill-2", "--c-text", "--c-text-2", "--c-text-3"]],
  ["Brand", ["--c-primary", "--c-primary-hover", "--c-primary-press", "--c-primary-tint", "--c-primary-tint-2"]],
  ["Status", ["--c-ok", "--c-ok-text", "--c-ok-bg", "--c-bad", "--c-bad-text", "--c-bad-bg", "--c-warn", "--c-warn-text", "--c-warn-bg", "--c-ai", "--c-ai-text", "--c-ai-bg"]],
  ["Charts", ["--c-chart-1", "--c-chart-2", "--c-chart-3", "--c-chart-4", "--c-chart-5"]],
];
const TYPE = [["--fs-3xl", "Large title"], ["--fs-2xl", "KPI value"], ["--fs-xl", "Section title"], ["--fs-lg", "Card headline"], ["--fs-md", "Body"], ["--fs-sm", "Secondary"], ["--fs-xs", "Caption"]];
const values = ref({});
onMounted(() => {
  const cs = getComputedStyle(document.documentElement);
  for (const [, list] of COLORS) for (const v of list) values.value[v] = cs.getPropertyValue(v).trim();
  for (const [v] of TYPE) values.value[v] = cs.getPropertyValue(v).trim();
});
const seg = ref("a"), sw = ref(true), stars = ref(4), field = ref("payment"), sheet = ref(false);
const pts = Array.from({ length: 30 }, (_, i) => [1_700_000_000 + i * 60, 3 + Math.sin(i / 3) * 1.4 + (i > 20 ? 2 : 0)]);
const steps = [{ label: "Detected", time: "10:02", state: "done" }, { label: "Analyzed", time: "10:04", state: "done" }, { label: "Approved", state: "current" }, { label: "Fixed", state: "todo" }, { label: "Verified", state: "todo" }];
</script>
<template>
  <div class="page">
    <UiPageHeader title="Design System" subtitle="Tokens and components every page is built from. Light Azure blue on Apple system greys, SF system font, iOS inset lists. Rendered live from the code." />
    <div class="section-label">Color tokens</div>
    <UiCard v-for="[group, list] in COLORS" :key="group" :title="group" class="mb">
      <div class="swatches"><div v-for="v in list" :key="v" class="sw"><span :style="{ background: `var(${v})` }" /><code>{{ v }}</code><small class="muted">{{ values[v] }}</small></div></div>
    </UiCard>
    <div class="section-label">Typography (system font: SF Pro / Sukhumvit Set)</div>
    <UiCard><div v-for="[v, l] in TYPE" :key="v" class="type"><span :style="{ fontSize: `var(${v})` }">{{ l }} อ่านง่าย</span><code class="muted">{{ v }} · {{ values[v] }}</code></div></UiCard>
    <div class="section-label">Buttons</div>
    <UiCard><div class="row row--wrap"><UiButton>Primary</UiButton><UiButton variant="tint">Tint</UiButton><UiButton variant="plain">Plain</UiButton><UiButton variant="danger">Danger</UiButton>
      <UiButton variant="ghost" icon="play">With icon</UiButton><UiButton loading>Loading</UiButton><UiButton disabled>Disabled</UiButton><UiButton size="sm">Small</UiButton></div>
      <UiButton size="lg" block class="mt">Large · full width (primary decision)</UiButton></UiCard>
    <div class="section-label">Status</div>
    <UiCard><div class="row row--wrap"><UiPill tone="ok">Resolved</UiPill><UiPill tone="bad">Fix didn't work</UiPill><UiPill tone="warn">New</UiPill><UiPill tone="ai">Needs approval</UiPill>
      <UiPill tone="info">Checking fix</UiPill><UiPill>Closed</UiPill><UiPill tone="solid-bad">Critical</UiPill><UiPill tone="solid-warn">Major</UiPill>
      <UiStatusDot tone="ok" /><UiStatusDot tone="bad" /><UiStatusDot tone="warn" /><UiStatusDot /></div>
      <UiStepper :steps="steps" class="mt" /></UiCard>
    <div class="section-label">Lists, tiles and logos</div>
    <UiList>
      <UiListRow to="/design" title="Payment Service" subtitle="v1.2.0 · 2.4 req/s · p95 95 ms"><template #leading><UiAppTile logo="python" status="ok" /></template><template #accessory>0.0% errors</template></UiListRow>
      <UiListRow to="/design" title="napat-mac" subtitle="CPU 17% · Memory 73% · Disk 92%"><template #leading><UiAppTile logo="apple" status="bad" /></template><template #accessory><UiPill tone="bad">Problem</UiPill></template></UiListRow>
      <UiListRow title="Failure rate increase" subtitle="P-12 · payment · 2 min ago" detail="Deployment v1.3.0 (commit d38c590) of payment introduced a regression"><template #leading><UiAppTile icon="warning" color="var(--c-bad)" /></template><template #accessory><UiPill tone="ai">Needs approval</UiPill></template></UiListRow>
    </UiList>
    <div class="grid grid--4 mt"><UiTile label="Open problems" :value="1" hint="14 in total" tone="bad" /><UiTile label="Time to detect" value="42 s" hint="average" />
      <UiMeter label="CPU" :value="42" /><UiMeter label="Disk" :value="92" /></div>
    <div class="section-label">Controls</div>
    <UiCard><div class="grid grid--2">
      <div><UiSegmented v-model="seg" :options="[{ value: 'a', label: 'All' }, { value: 'b', label: 'Problems only' }, { value: 'c', label: 'macOS', logo: 'apple' }]" label="Example" />
        <div class="row mt"><UiSwitch v-model="sw" label="Example switch" /><span>Owner switch: {{ sw ? "on" : "off" }}</span></div>
        <UiStars v-model="stars" class="mt" /></div>
      <div><UiField v-model="field" label="Text field" hint="(hint)" /><UiButton variant="tint" class="mt" @click="sheet = true">Open sheet</UiButton></div></div></UiCard>
    <div class="section-label">Data</div>
    <div class="grid grid--2"><UiAreaChart title="Requests / s" :points="pts" /><UiCard title="Code block"><UiCodeBlock code="curl -fsSL http://cp26pt1.sit.kmutt.ac.th:8080/install/agent.sh | sh" /></UiCard></div>
    <div class="grid grid--2 mt"><UiWait title="Waiting for my-mac…" subtitle="This updates by itself." /><UiWait done title="my-mac is connected" subtitle="CPU 12% · Memory 70%" /></div>
    <UiSheet v-model="sheet" title="Sheet"><p class="muted">Centered on desktop, slides up from the bottom on phones.</p>
      <template #footer><UiButton variant="plain" @click="sheet = false">Cancel</UiButton><UiButton @click="sheet = false">Done</UiButton></template></UiSheet>
  </div>
</template>
<style scoped>
.mb { margin-bottom: 12px; }
.swatches { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.sw { display: flex; flex-direction: column; gap: 4px; font-size: 12px; }
.sw span { height: 44px; border-radius: 10px; box-shadow: inset 0 0 0 0.5px var(--c-separator); }
.type { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding: 8px 0; border-bottom: 0.5px solid var(--c-separator); }
</style>
